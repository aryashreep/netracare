# NetraCare

> An AI front desk for a fictional eye clinic — a six-iteration Agentic AI
> capstone. Fictional clinic. Synthetic data only.

## How this repo is organized

Each capstone iteration lives on its own long-lived branch and only
merges to `main` after that iteration's demo is complete. This keeps
`main` demo-ready and gives each iteration its own PR for review.

| # | Iteration | Branch | Status |
|---|---|---|---|
| 1 | Booking foundation (FastAPI + rules engine, Next.js UI) | [`iteration-1`](../../tree/iteration-1) | In review |
| 2 | First LLM features (Fact of the Day, red-flag check, doctor summary) | `iteration-2` | Not started |
| 3 | Patient chat with RAG (hybrid search, citations, "I don't know") | `iteration-3` | Not started |
| 4 | Agent (LangGraph wrapping the Iter-1 API as tools) | `iteration-4` | Not started |
| 5 | Evals + observability (RAGAS, LangSmith / Opik) | `iteration-5` | Not started |
| 6 | Voice + MCP server (partner-app access) | `iteration-6` | Not started |

For the full architecture, workflow, and run instructions, open the
README on the most recent iteration branch.

Governance (spec-kit workflow, constitution, protected files) lives on
every iteration branch under `.specify/` and `docs/conventions.md`.
