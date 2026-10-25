"""The manual tool-use loop: give Claude the four MarketLens tools, let it decide
which to call, run them, feed results back, repeat until it's done or a limit hits."""

from app.claude_client import create_turn
from app.tools import TOOL_DEFINITIONS, dispatch


class ToolLoopLimitExceeded(Exception):
    pass


def run_tool_loop(user_content, max_turns: int = 6, tool_choice: dict | None = None):
    """Run the loop to completion. Returns (final Message, tools_called) — tools_called
    is the ordered list of tool names actually invoked, across every turn.

    tool_choice (if given) applies ONLY to the first turn. Forcing "any" or a specific
    tool on every turn would force Claude to keep calling tools even after it already
    has what it needs to answer — the forced choice should kick off the loop, not
    hold it hostage.

    Raises ToolLoopLimitExceeded if Claude keeps calling tools past max_turns — a
    budget/termination guard, not just a nice-to-have."""
    messages = [{"role": "user", "content": user_content}]
    tools_called = []

    for turn in range(max_turns):
        current_tool_choice = tool_choice if turn == 0 else None
        message = create_turn(messages, tools=TOOL_DEFINITIONS, tool_choice=current_tool_choice)

        if message.stop_reason != "tool_use":
            return message, tools_called

        messages.append({"role": "assistant", "content": message.content})

        tool_results = []
        for block in message.content:
            if block.type != "tool_use":
                continue
            tools_called.append(block.name)
            content, is_error = dispatch(block.name, block.input)
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": content,
                    "is_error": is_error,
                }
            )

        messages.append({"role": "user", "content": tool_results})

    raise ToolLoopLimitExceeded(f"Tool loop did not finish within {max_turns} turns.")
