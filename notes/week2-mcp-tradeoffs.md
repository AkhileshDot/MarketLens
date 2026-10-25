# Week 2 (cont.) — MCP server

## Main trade-off: stdio vs. Streamable HTTP, built both, default to stdio

**Decision:** `mcp_server/server.py` defaults to stdio transport (`python -m
mcp_server.server`) and supports Streamable HTTP as an opt-in (`... http`, on its own
port 8001 so it never collides with the FastAPI backend).

**Why stdio is the default:** stdio is a one-client-per-process model — the MCP client
(e.g. Claude Desktop, or this project's own tests) spawns the server as a subprocess
and talks to it over stdin/stdout. No network port is ever opened, so there's nothing
to secure, firewall, or accidentally expose — the strongest form of "least privilege"
for a tool server that only this machine's own tooling should ever reach.

**Why Streamable HTTP still exists:** it's needed the moment more than one client
needs to reach the same running server, or the server needs to live on different
infrastructure than its client (e.g. a shared MCP server multiple teammates' Claude
Desktop instances connect to, or a server that outlives any single client session).
Verified live: both transports expose the identical four tools and the resource
template — the business logic layer doesn't know or care which transport is in use.

**Exam angle:** this is the MCP-specific version of the stdio-vs-HTTP trade-off that
shows up everywhere in the exam (sync vs. async, streaming vs. batch): pick the
narrowest-scope option by default, broaden only when a real multi-client/remote
requirement shows up.

## Secondary trade-off: MCP tools reuse the data layer directly, not app/tools.py's dispatch()

**Decision:** `mcp_server/server.py`'s tool functions call `get_quote()`,
`get_daily_prices()`, etc. directly from `app/data_source.py` — they do **not** go
through `app/tools.py`'s `dispatch()` (the function used by the in-process manual tool
loop).

**Why:** `dispatch()`'s `(content, is_error)` tuple return and manual required-field
validation exist specifically for the Anthropic Messages API's `tool_result` block
shape. MCP has its own, different error-signaling convention — raising `ToolError`
(caught by the framework and turned into a protocol-level `is_error` result) rather
than returning a tuple. And MCP's `input_schema` is auto-generated from the Python
function signature, so hand-maintaining `app/tools.py`'s manual JSON Schema a second
time for MCP would just be duplicated, driftable work. The two tool "front ends"
(manual loop vs. MCP) share the same underlying data functions but have their own
thin adapter layer matching their own protocol's conventions.

## Real bugs hit while building this

1. **API drift in the `mcp` SDK itself**: `FastMCP` was renamed to `MCPServer` between
   major versions (`mcp` 1.x → 2.x) — the exact "SDK behavior is generation-specific"
   lesson from Week 1's `temperature` bug, this time one layer further out (a
   dependency's own breaking change, not Anthropic's API).
2. **Wrong exception type for graceful tool errors**: raising a plain `ValueError`
   inside an MCP tool function crashed as an `UnexpectedToolError` instead of
   producing a clean `is_error: true` result — the SDK specifically distinguishes
   `ToolError` (expected, becomes a graceful protocol-level error) from any other
   exception (treated as a genuine server bug). Lesson: a framework's "how do I
   signal an expected failure" convention is never safe to assume from a different
   framework's convention (this is the opposite shape from Anthropic's "catch
   whatever, build an `is_error` tuple yourself" pattern in `app/tools.py`).
3. **Windows console encoding**: `Path.read_text()` without `encoding="utf-8"` used
   the OS default (`cp1252`) and silently mangled the `—` character in a sample
   report file. Same class of bug as earlier (printing ₹ crashed the Windows
   console) — always pass `encoding="utf-8"` explicitly when reading text files
   whose content isn't guaranteed ASCII, rather than trusting the platform default.
