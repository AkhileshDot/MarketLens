# Week 2 — Tools and the manual tool-use loop

## Main trade-off: force tool_choice on turn 1 only, not every turn

**Decision:** `run_tool_loop()` applies the caller's `tool_choice` (e.g. `any`, or a
specific tool) only to the loop's first API call. Every subsequent turn uses the
default (`auto`), regardless of what was requested.

**Rejected alternative:** apply the same forced `tool_choice` on every turn of the loop.

**Why rejected:** forcing `any` or a specific tool is meant to *kick off* the loop in
a known way — not to hold it hostage. If turn 2 re-forces "must call a tool," Claude
is denied the ability to ever reach `end_turn` once it has the data it needs; it would
be compelled to keep calling tools indefinitely (bounded only by `max_turns`, which
would then always fire as an error instead of a real termination). Verified live:
forcing `get_financials` on turn 1 still let the model additionally call `get_quote`
on turn 2 via its own judgment (`auto`) once the forced call's result came back —
proving the loop can still finish naturally after an initial forced call.

**Exam angle:** CCDV-F likely tests whether you understand `tool_choice` as a
per-request setting, not a loop-wide policy — a forced choice that never relaxes is a
classic way to accidentally build an agent that can't stop.

## Finding: tool_choice=none can produce an empty response, not a wrong one

Asking "What is the current price of NSE:INFY?" with `tool_choice=none` (tools
available but forbidden from being called) returned a response with **zero text
content** — only an empty-text thinking block, `stop_reason: end_turn`. Confirmed this
is question-dependent, not a bug: the same call with a general-knowledge question
("What does a P/E ratio mean?") returned a normal, detailed answer.

**Interpretation:** the model's system prompt instructs "explain, never guess" — when
it has no path to real data (tools forbidden) and no general knowledge that answers the
question truthfully, it appears to prefer producing nothing over fabricating a number.
This is arguably *correct* and safe behavior for a finance app, but it's also a sharp
edge: naively rendering `extract_text(message)` as-is would show the user a silent,
confusing blank response. We now detect this specific case (`tool_choice == "none"` and
an empty answer) and surface an explicit explanation instead.

**Exam angle:** a stop_reason of `end_turn` does not guarantee non-empty content — don't
assume "the call succeeded" means "there's something to show the user."

## Agent Skill (SKILL.md) vs. baking the same content into SYSTEM_PROMPT

**Decision:** note format and ratio definitions (P/E, ROE, debt-to-equity) are packaged
as a Claude Code project skill (`.claude/skills/marketlens-notes/SKILL.md`), not added
to `claude_client.py`'s `SYSTEM_PROMPT`.

**Rejected alternative:** paste the same formulas/format guidance directly into the
system prompt sent on every single Messages API call.

**Why rejected — and an important distinction:** an Agent Skill is a **Claude Code
session-level concept** (loaded on-demand when the task shape matches, e.g. "write a
note" or "explain P/E"), not a feature the deployed FastAPI app can invoke through the
Messages API at request time. So this skill is genuinely useful while *developing*
MarketLens with Claude Code (consistent formula explanations, consistent note
structure, surfaced only when relevant) — but it does **not** by itself make the live
`/analyze` endpoint's output follow this format. For that, the formulas/format still
need to live in `SYSTEM_PROMPT` (paying their token cost on every request) or, later,
be wired in via the Claude *API's* own Skills feature (`container={"skills": [...]}`,
a different mechanism from Claude Code project skills, despite the similar name).

**Exam angle:** "Agent Skills" is genuinely two different things depending on the
surface — a Claude Code/Claude.ai convenience that loads instructions into *the
assistant's own context* on demand, vs. the Claude API's own skills container feature
for code-execution-backed document generation. Confusing the two is an easy trap.

## Secondary trade-off: validate required tool fields ourselves vs. trust the JSON Schema

**Decision:** `dispatch()` in `app/tools.py` checks `required` fields itself before
calling the underlying function, even though `input_schema` already declares them.

**Rejected alternative:** trust that Claude always supplies every field the schema
marks required, and let a missing field surface as a Python `KeyError` instead.

**Why rejected:** `input_schema` is a strong hint to the model, not an API-enforced
contract on Claude's output in the way a strict server-side validator would be (unless
`strict: true` is set, which this project doesn't use yet). A missing field becoming an
unhandled `KeyError` would crash the whole turn instead of giving Claude an
`is_error: true` tool_result it can react to (e.g. by asking a clarifying question or
retrying with the right input). Defense in depth: never assume the caller — even
Claude itself — perfectly honored the schema.
