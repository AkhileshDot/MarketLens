# Week 3 — Workflow vs. Agent

## Main comparison: deterministic workflow (`app/workflow.py`) vs. autonomous agent (`agents/single_agent.py`)

Both were built to answer the same kind of question, over the same four data sources
(via the same MCP server, for the agent version). Ran both live, not just read about
the difference:

| | Workflow (`run_workflow`) | Agent (`run_single_agent`) |
|---|---|---|
| **Steps** | Fixed: fetch all 4 sources → analyze → write. Always 2 Claude calls. | Variable: Claude's own harness decides what to call and how many turns. |
| **Data fetched for "price trend + ratios" question** | All 4 sources, every time — news included even though unused. | Only `get_quote`, `get_ohlc`, `get_financials`. Explicitly skipped news and said why. |
| **Predictability** | Fully predictable: same steps, same cost shape, every call. | Variable: turn count, tool calls, and even model behavior (see bug below) differ run to run. |
| **Dependencies** | Just the Anthropic SDK, already in use everywhere else. | `claude-agent-sdk` (123MB install) + the `claude` CLI binary + spawns the MCP server as a subprocess — real infra, not just a library import. |
| **Latency** | Two sequential Claude calls. | Several turns (tool search, tool call, more thinking, final text) — noticeably slower per request, more orchestration overhead. |
| **Source citation** | Had to explicitly prompt "list your sources" in the write step. | Fell out naturally — the agent was explicitly asked which tools it used and listed them correctly, because it called real named tools rather than being fed pre-fetched data. |

**Decision:** the workflow version is the right default for `/analyze` and `/chat` —
predictable cost, no extra infra, and the ticker + days + file inputs don't actually
vary enough to need Claude deciding its own data-fetching plan. The agent version is
the right fit for genuinely open-ended questions (the kind `/ask` was built for) where
what data is relevant isn't knowable in advance.

**Rejected alternative:** using the agent version everywhere, for consistency. Rejected
because the fixed four-call shape of `/analyze` doesn't benefit from Claude's own
judgment about what to fetch — it already always needs the same four things, so paying
for an extra harness layer (process spawn, tool search turn, more tokens) buys nothing.

**Exam angle:** this is the generic "when do you need an agent vs. a workflow" decision
from the exam's own framing — complexity, value, viability, cost-of-error. A fixed,
well-specified task (fetch these 4 things, always) stays a workflow; genuinely
open-ended input (a free-text question of unknown shape) justifies the agent.

## Why the agent version isn't in the automated pytest suite

`agents/single_agent.py` spawns two real subprocesses (the `claude` CLI, and our MCP
server as its child) and makes real, billed Anthropic API calls — there's no practical
way to unit-test it with mocks without testing nothing meaningful (the entire point is
the SDK's own orchestration). Verified manually, live, instead; `app/workflow.py` and
`app/tool_loop.py` (Weeks 1-2) remain fully mocked and in the fast suite, since those
are our own code and the right target for unit tests.

## Orchestrator-worker: permission scoping is additive top-down, not independent per-subagent

**Bug hit building `agents/orchestrator.py`:** gave each subagent its own narrow
`AgentDefinition.tools` list (e.g. the `news` subagent only `search_news`), and set
the top-level session's `allowed_tools=["Task"]` (the orchestrator "only delegates").
Every subagent's tool call was silently blocked with `permission_denied` — the
orchestrator's final note still came back looking plausible, which is the dangerous
part: it would be easy to ship this without noticing, since nothing crashes.

**Root cause:** a subagent's own `tools` list only *narrows* what the top-level
session's `allowed_tools` already grants — it cannot grant anything beyond that
superset. So the top-level list must include every tool any subagent might call, even
though the orchestrator itself never calls them directly. Fix: `allowed_tools =
["Agent", *all_mcp_tools_across_every_subagent]`.

**Secondary naming bug:** the delegation tool is called `Agent` in the installed SDK
version, not `Task` — discovered by inspecting live `ToolUseBlock.name` values rather
than trusting a guess from the dataclass field name (`agents=`) or general docs
familiarity.

**Exam angle:** least-privilege scoping across an orchestrator-worker hierarchy is
additive from the top down, not independently enforced per level. A security review
that only checks "does this subagent's own tool list look narrow enough" without
checking the parent session's grant would miss that the whole thing is either too
permissive (parent grants more than any subagent declares) or silently broken (parent
grants less than a subagent needs, and the failure doesn't surface loudly).

## Real finding: the same debt-to-equity figure got two different (both reasonable) interpretations

`get_financials` returns `debt_to_equity: 8.567` for NSE:INFY. In the workflow version,
Claude flagged this as implausibly high for a low-debt IT company and recommended
verification. In the agent version, Claude instead reasoned that `yfinance` commonly
reports this field as a percentage (so ~8.6%, i.e. ~0.09x) and interpreted it as
plausible. Both are defensible readings of an ambiguous raw number — this is a genuine
data-quality gap in the source, not a bug in either code path, and a good illustration
of why "cite your source, don't just report a bare number" (the note-format skill's
rule) matters: a reader seeing "8.567" with no units context could draw either
conclusion with no way to tell which is right.
