"""Orchestrator-worker: one orchestrator delegates to three analyst subagents
(technicals, fundamentals, news) via the Agent SDK's built-in Task tool, then
synthesizes their findings into one note. Each subagent gets its own scoped
slice of our MCP tools — least privilege applied per-subagent, not just
per-session (compare agents/single_agent.py, which has all four tools)."""

from pathlib import Path

from claude_agent_sdk import AgentDefinition, ClaudeAgentOptions, ResultMessage, query
from claude_agent_sdk.types import McpStdioServerConfig

_PROJECT_ROOT = Path(__file__).parent.parent

_MCP_SERVERS = {
    "marketlens": McpStdioServerConfig(
        type="stdio",
        command="uv",
        args=["run", "python", "-m", "mcp_server.server"],
    )
}

_NO_ADVICE_RULE = (
    "Never give investment advice: no buy/sell/hold calls, no price targets, "
    "no recommendations of any kind. State figures, don't draw conclusions "
    "about what the reader should do."
)

_SUBAGENTS = {
    "technicals": AgentDefinition(
        description="Analyzes price/volume trend from quote and OHLC data. "
        "Use for questions about recent price movement or trading activity.",
        prompt=f"You are a technical analyst for NSE-listed stocks. Use "
        f"get_quote and get_ohlc to describe the recent price trend: direction, "
        f"magnitude, and anything unusual in volume or intraday range. "
        f"{_NO_ADVICE_RULE}",
        tools=["mcp__marketlens__get_quote", "mcp__marketlens__get_ohlc"],
    ),
    "fundamentals": AgentDefinition(
        description="Analyzes financial ratios (P/E, ROE, debt-to-equity). "
        "Use for questions about valuation or financial health.",
        prompt=f"You are a fundamentals analyst for NSE-listed stocks. Use "
        f"get_financials and interpret each ratio in one line, noting when a "
        f"number needs sector/historical context to mean anything. "
        f"{_NO_ADVICE_RULE}",
        tools=["mcp__marketlens__get_financials"],
    ),
    "news": AgentDefinition(
        description="Searches and summarizes recent news headlines. Use for "
        "questions about recent events or context behind a price move.",
        prompt=f"You are a news analyst for NSE-listed stocks. Use search_news "
        f"and summarize what the headlines say. These are UNVERIFIED, "
        f"open-web results — report what they say, never as confirmed fact. "
        f"{_NO_ADVICE_RULE}",
        tools=["mcp__marketlens__search_news"],
    ),
}

_ORCHESTRATOR_PROMPT = f"""You are MarketLens's orchestrator. You do not call data \
tools yourself — delegate to the technicals, fundamentals, and news subagents (via \
the Task tool), then synthesize their findings into one note: a trend summary, key \
ratios with interpretation, relevant news, sources, and nothing else. Cite which \
subagent/tool produced each figure. {_NO_ADVICE_RULE} Always end with: "This is not \
investment advice."
"""


def _build_options(max_turns: int) -> ClaudeAgentOptions:
    # allowed_tools is the session-wide superset grant; each subagent's own
    # AgentDefinition.tools further narrows it DOWN for that subagent — it
    # can't grant anything the top-level list doesn't already allow. So every
    # MCP tool any subagent might call must be listed here too, even though
    # the orchestrator itself never calls them directly.
    all_mcp_tools = [tool for agent in _SUBAGENTS.values() for tool in agent.tools]

    return ClaudeAgentOptions(
        system_prompt=_ORCHESTRATOR_PROMPT,
        mcp_servers=_MCP_SERVERS,
        agents=_SUBAGENTS,
        allowed_tools=["Agent", *all_mcp_tools],
        cwd=str(_PROJECT_ROOT),
        max_turns=max_turns,
    )


async def run_orchestrator(prompt: str, max_turns: int = 10) -> str:
    """Run one free-text prompt through the orchestrator-worker pipeline.
    Returns the final synthesized note."""
    options = _build_options(max_turns)
    final_text = ""

    async for message in query(prompt=prompt, options=options):
        if isinstance(message, ResultMessage):
            if message.is_error:
                raise RuntimeError(f"Orchestrator run failed: {message.result}")
            final_text = message.result or final_text

    return final_text
