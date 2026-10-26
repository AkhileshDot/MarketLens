"""The 'agent' half of Week 3's comparison: Claude Agent SDK, autonomous.

Unlike app/workflow.py (we decide every step) or app/tool_loop.py (our own
hand-written tool-use loop), this uses the Claude Agent SDK's own harness —
its own session, its own tool-use loop, its own MCP client — wired to our
existing MCP server (mcp_server/server.py, exposed via .mcp.json) as its ONLY
tool source. No built-in file/bash tools are allowed, matching the project's
read-only, least-privilege ground rules.
"""

from pathlib import Path

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query
from claude_agent_sdk.types import McpStdioServerConfig

_PROJECT_ROOT = Path(__file__).parent.parent

SYSTEM_PROMPT = """You are MarketLens, a research assistant for NSE-listed stocks.

Explain trends, ratios and recent events using only the data provided. Never give \
investment advice: no buy/sell/hold calls, no price targets, no recommendations of any \
kind. If asked for a recommendation, explain that you provide analysis only.

Always include a one-line disclaimer at the end: "This is not investment advice."
"""

# The SDK namespaces MCP tools as mcp__<server_name>__<tool_name>, matching the
# "marketlens" key below and the four tool names from mcp_server/server.py.
ALLOWED_TOOLS = [
    "mcp__marketlens__get_quote",
    "mcp__marketlens__get_ohlc",
    "mcp__marketlens__get_financials",
    "mcp__marketlens__search_news",
]


def _build_options(max_turns: int) -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        mcp_servers={
            "marketlens": McpStdioServerConfig(
                type="stdio",
                command="uv",
                args=["run", "python", "-m", "mcp_server.server"],
            )
        },
        allowed_tools=ALLOWED_TOOLS,
        cwd=str(_PROJECT_ROOT),
        max_turns=max_turns,
    )


async def run_single_agent(prompt: str, max_turns: int = 6) -> str:
    """Run one free-text prompt through the agent. Returns the final text answer.

    Nothing here decides which data to fetch — Claude does, autonomously, same
    autonomy as app/tool_loop.py's hand-written loop, but delegated to the Agent
    SDK's own harness instead of code we wrote ourselves."""
    options = _build_options(max_turns)
    final_text = ""

    async for message in query(prompt=prompt, options=options):
        if isinstance(message, ResultMessage):
            if message.is_error:
                raise RuntimeError(f"Agent run failed: {message.result}")
            final_text = message.result or final_text

    return final_text
