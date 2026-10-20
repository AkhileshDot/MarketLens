# Week 0 — Data source decision

**Decision:** Use `yfinance` (free, public) for prices/OHLC/fundamentals and public RSS
feeds for news. No broker API integration anywhere in the project.

**Rejected alternative:** Kite Connect (or any broker API).

**Why rejected:** Broker APIs earn their cost/complexity for *live intraday quotes* and
*order execution*. MarketLens is explain-only research with no trading — there is no
execution path, and end-of-day data is sufficient for trend/ratio/news analysis. Using a
broker API here would add paid-tier cost (Kite's historical data is a paid add-on), KYC/
account setup overhead, and a redistribution-rights question for exchange data, while
adding zero capability for this use case. It would also widen the compliance surface
for no reason — the project's "read-only, no order tool" guarantee is stronger when
there is no broker credential in the system at all, rather than relying on scoping a
broker key down to read-only.

**Exam angle:** This is a model/tool **selection under constraints** trade-off — pick the
least-privileged, lowest-cost data source that satisfies the actual use case, not the
most "production-grade" looking one. Scenario questions often test whether you reach for
a heavier integration than the stated requirements call for.
