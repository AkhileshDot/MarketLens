from unittest.mock import MagicMock, patch

import pytest

from app.tool_loop import ToolLoopLimitExceeded, run_tool_loop


def _end_turn_message(text: str = "Done."):
    block = MagicMock(type="text", text=text)
    return MagicMock(stop_reason="end_turn", content=[block])


def _tool_use_message(tool_name: str, tool_input: dict, tool_use_id: str = "tool_1"):
    # NB: MagicMock's constructor reserves `name=` for its own repr — set it as an
    # attribute afterward instead, or it silently won't become block.name.
    block = MagicMock(type="tool_use", input=tool_input, id=tool_use_id)
    block.name = tool_name
    return MagicMock(stop_reason="tool_use", content=[block])


@patch("app.tool_loop.create_turn")
def test_returns_immediately_when_no_tool_use(mock_create_turn):
    mock_create_turn.return_value = _end_turn_message()

    message, tools_called = run_tool_loop("Say hi")

    assert message.stop_reason == "end_turn"
    assert mock_create_turn.call_count == 1
    assert tools_called == []


@patch("app.tool_loop.dispatch")
@patch("app.tool_loop.create_turn")
def test_runs_one_tool_call_then_finishes(mock_create_turn, mock_dispatch):
    mock_create_turn.side_effect = [
        _tool_use_message("get_quote", {"ticker": "NSE:INFY"}),
        _end_turn_message("Here's the price."),
    ]
    mock_dispatch.return_value = ('{"last_price": 1150}', False)

    message, tools_called = run_tool_loop("What's the price of NSE:INFY?")

    assert message.stop_reason == "end_turn"
    assert mock_create_turn.call_count == 2
    assert tools_called == ["get_quote"]
    mock_dispatch.assert_called_once_with("get_quote", {"ticker": "NSE:INFY"})

    # The second call's messages must include the tool_result we built.
    second_call_messages = mock_create_turn.call_args_list[1].args[0]
    tool_result_message = second_call_messages[-1]
    assert tool_result_message["role"] == "user"
    assert tool_result_message["content"][0]["type"] == "tool_result"
    assert tool_result_message["content"][0]["tool_use_id"] == "tool_1"
    assert tool_result_message["content"][0]["is_error"] is False


@patch("app.tool_loop.dispatch")
@patch("app.tool_loop.create_turn")
def test_tool_choice_only_forced_on_first_turn(mock_create_turn, mock_dispatch):
    mock_create_turn.side_effect = [
        _tool_use_message("get_quote", {"ticker": "NSE:INFY"}),
        _end_turn_message("Here's the price."),
    ]
    mock_dispatch.return_value = ("{}", False)

    run_tool_loop("price?", tool_choice={"type": "any"})

    first_call_kwargs = mock_create_turn.call_args_list[0].kwargs
    second_call_kwargs = mock_create_turn.call_args_list[1].kwargs
    assert first_call_kwargs["tool_choice"] == {"type": "any"}
    assert second_call_kwargs["tool_choice"] is None


@patch("app.tool_loop.create_turn")
def test_raises_when_loop_never_finishes(mock_create_turn):
    mock_create_turn.return_value = _tool_use_message("get_quote", {"ticker": "NSE:INFY"})

    with pytest.raises(ToolLoopLimitExceeded):
        run_tool_loop("Keep going forever", max_turns=3)

    assert mock_create_turn.call_count == 3
