# Week 1 — Streaming vs. Batches (and a few smaller ones)

## Main trade-off: synchronous streaming (`/chat`) vs. Message Batches API

**Decision:** `/chat` uses live SSE streaming (`messages.stream()`), not the Batches API.

**Rejected alternative:** Message Batches API for this endpoint.

**Why rejected:** Batches trades latency for cost — results arrive asynchronously
(minutes, not seconds) at roughly half the per-token price, and are meant for
non-interactive, high-volume workloads where nobody is watching a screen waiting for
the answer. `/chat` is a live, user-facing endpoint — a person typed a ticker and is
looking at the response as it's generated. Using Batches here would mean polling a job
status for an answer the user expects immediately; it optimizes for the wrong thing.

Batches is the right fit for Week 4's nightly Nifty 50 scan (50 tickers, unattended,
cost-sensitive, no one waiting on a particular result) — same company, different access
pattern, different trade-off outcome.

**Exam angle:** CCDV-F scenario questions on "Applications and Integration" often hinge
on exactly this — matching the API surface to whether a human is waiting synchronously
or not. Streaming and Batches aren't "better/worse," they're tuned for opposite points on
the latency-vs-cost curve.

## Secondary trade-off: no retry wrapper on `stream_message()`

**Decision:** `create_message()` (used by `/analyze`) has a `tenacity` retry decorator
for 429/529; `stream_message()` (used by `/chat`) does not.

**Rejected alternative:** reuse the same retry decorator on the streaming function.

**Why rejected:** A non-streaming call either fully succeeds or fully fails — retrying
is safe because nothing was shown to the user yet. A stream can fail *partway through*,
after several chunks have already been flushed to the client. A naive retry would
re-run the whole request and send the beginning of the note twice. Handling this
correctly needs stream-aware retry logic (e.g., only retry if zero bytes have been sent
yet), which this project's scope doesn't require — the trade-off is accepted and
documented rather than solved.

## Smaller note: API drift on sampling parameters

Hit a real `TypeError` passing `temperature` to `messages.create()` — on current-gen
models (Sonnet 5+), `temperature`/`top_p`/`top_k` are removed entirely, replaced by
`output_config.effort` + adaptive thinking. Lesson: SDK/API behavior is generation-
specific; code written against training-data knowledge of an older API shape can be
silently wrong until it's actually run.

## Multimodal input: base64 inline vs. the Files API

**Decision:** images/PDFs are base64-encoded inline into each request's content block
(`build_content_block()` in `app/file_input.py`).

**Rejected alternative:** upload the file once via the Files API, then reference it by
`file_id` in the request.

**Why rejected:** the Files API earns its cost when the *same* file is reused across
multiple requests (upload once, reference many times — saves re-sending bytes). Here,
each `/analyze`/`/chat` call is a one-shot "look at this chart alongside this ticker's
data" — there's no reuse. Inline base64 is simpler (no second API call, no file
lifecycle to manage) and correct for the access pattern. Would revisit if a future
feature needs to reference the same uploaded document across several turns of a
conversation or several subagents (Week 3).

## Bug found via this feature: content[0] isn't reliably the text block

Discovered that `message.content[0].text` broke with `AttributeError: 'ThinkingBlock'
object has no attribute 'text'` the first time a real request triggered adaptive
thinking. Current-gen models (Sonnet 5+) run adaptive thinking **by default** — nothing
about multimodal input caused this, it was a pre-existing latent bug that a slower/more
complex multimodal prompt simply had a higher chance of triggering (thinking is more
likely to kick in on harder prompts). Fixed with `extract_text()`, which filters
`message.content` for `type == "text"` blocks instead of indexing position 0.

**Exam angle:** never assume response content block ordering/shape is stable across
model generations — always check `.type` before reading type-specific fields.

## Smaller note: GET vs POST for `/chat`

`/chat` moved from `GET` with query params to `POST` with multipart form data, to carry
an optional file upload (browsers' native `EventSource` only supports `GET`, so a real
frontend would need `fetch()` + manual stream reading instead of `EventSource` here —
accepted, since this project's clients are curl/Python, not a browser `EventSource`).
