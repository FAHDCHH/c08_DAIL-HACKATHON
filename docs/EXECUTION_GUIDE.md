# Execution guide

## Architecture
```
Next.js console (3000) ──HTTP──▶ FastAPI (8000) ──▶ Postgres (db)
   demo-key gate                    │  one structured agent pass
   annotated report doc             │  (DeepSeek, OpenAI-compatible; mock fallback)
   history + PDF download           └▶ ReportLab ─▶ reports_out/*.pdf
```
Three containers via `docker compose`: `frontend`, `api`, `db`.

## The agent (one pass)
`app/agent.py` — deterministic code parses report JSON into immutable evidence records; a single
structured LLM call (context file + evidence → JSON draft) produces claims (text, value, unit, period,
evidence_ids, status, reasoning), conflicts and follow-up suggestions. Schema-validated with Pydantic.
Evidence-on-demand is a pure DB lookup (no extra call). `AGENT_MODE=mock` returns a canned draft.

## Context file = the config that makes it company-agnostic
`contexts/*.json`: program, terminology (e.g. attended vs completed), rules (numeric claim needs
unit+period+record; draft until approved; no outcome from participation), metrics, report schema.
Change the file, not the agent.

## State machine
`draft → approved`. New evidence resets to draft. A note-driven **revise** proposes a new draft +
regenerates the PDF; the officer **accepts** (kept, stored in `revisions`) or **refuses** (reverts to
the snapshot). Every generated PDF is recorded in `generated_reports` (searchable, downloadable).

## Key endpoints
| Method | Path | Purpose |
|---|---|---|
| GET | `/events?q=` | list events by name, `needs_attention` flag |
| POST | `/scenarios/{id}/load` | create an event from a synthetic scenario |
| POST | `/events/{id}/reports` | a new report arrives (unprocessed until re-analyze) |
| POST | `/events/{id}/analyze` | run the agent → draft |
| GET | `/events/{id}/report` | claims + suggestions + verbatim evidence |
| GET | `/claims/{id}/evidence` | evidence-on-demand (source + reasoning) |
| POST | `/claims/{id}/annotations` | officer note on a claim |
| POST | `/events/{id}/revise` | note → re-generate + new PDF (proposed) |
| POST | `/revisions/{id}/decision` | accept (store) / refuse (revert) |
| POST | `/suggestions/{id}/decision` | keep / dismiss |
| POST | `/events/{id}/approve` | draft → approved, generate PDF |
| GET | `/reports?q=` | report history, searchable by event name |
| GET | `/reports/{id}/download` | download a generated PDF |

## Config (.env)
`AGENT_PROVIDER` (deepseek|anthropic) · `AGENT_MODE` (live|mock) · `AGENT_MODEL` ·
`DEEPSEEK_API_KEY` · `DATABASE_URL` · `DEMO_CODE` (frontend gate).

## Reset / logs
```bash
docker compose down -v && docker compose up -d   # fresh DB
docker compose logs -f api                        # backend logs
```
