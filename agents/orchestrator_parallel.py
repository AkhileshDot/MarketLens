"""True parallel orchestrator-worker.

agents/orchestrator.py delegates via the Agent SDK's internal Agent tool —
verified live that this SERIALIZES subagent execution within one session, even
with run_in_background=true (growing completion gaps, not concurrent
completions; see notes/week3-tradeoffs.md). This module instead runs the three
subagents as independent query() sessions via asyncio.gather — confirmed via
asyncio.gather(3 independent query() calls) to actually overlap in wall-clock
time (overall ≈ slowest individual call, not their sum). A final synthesis
step combines their findings with one plain Messages API call — no agent
harness needed for synthesis, it's just text.
"""

import asyncio

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query

from agents.orchestrator import _MCP_SERVERS, _NO_ADVICE_RULE, _PROJECT_ROOT, _SUBAGENTS
from app.claude_client import create_message, extract_text


async def _run_subagent(name: str, question: str, max_turns: int) -> str:
    agent_def = _SUBAGENTS[name]
    options = ClaudeAgentOptions(
        system_prompt=agent_def.prompt,
        mcp_servers=_MCP_SERVERS,
        allowed_tools=agent_def.tools,
        cwd=str(_PROJECT_ROOT),
        max_turns=max_turns,
    )

    final_text = ""
    async for message in query(prompt=question, options=options):
        if isinstance(message, ResultMessage):
            if message.is_error:
                raise RuntimeError(f"{name} subagent failed: {message.result}")
            final_text = message.result or final_text

    return final_text


def _synthesize(question: str, findings: dict[str, str]) -> str:
    """One plain Messages API call — synthesis is pure text combination, it
    doesn't need tools or an agent harness."""
    prompt = (
        f"Original question: {question}\n\n"
        f"Combine these three subagents' findings into one polished research "
        f"note: a trend summary, key ratios with interpretation, relevant news, "
        f"and sources (name which subagent produced each figure). "
        f"{_NO_ADVICE_RULE} End with: \"This is not investment advice.\"\n\n"
        f"TECHNICALS SUBAGENT FOUND:\n{findings['technicals']}\n\n"
        f"FUNDAMENTALS SUBAGENT FOUND:\n{findings['fundamentals']}\n\n"
        f"NEWS SUBAGENT FOUND:\n{findings['news']}"
    )
    message = create_message(prompt)
    return extract_text(message)


async def run_parallel_orchestrator(question: str, max_turns: int = 6) -> str:
    """Run all three subagents concurrently, then synthesize. Genuine
    wall-clock parallelism — see module docstring for why this differs from
    agents/orchestrator.py."""
    technicals, fundamentals, news = await asyncio.gather(
        _run_subagent("technicals", question, max_turns),
        _run_subagent("fundamentals", question, max_turns),
        _run_subagent("news", question, max_turns),
    )
    findings = {"technicals": technicals, "fundamentals": fundamentals, "news": news}
    return _synthesize(question, findings)
