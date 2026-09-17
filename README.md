# Evidence Console — C08 (Schmitz-Stiftungen, exercise demo)

Turns mixed, conflicting field reports about one event into a **reviewable progress report** where every claim is traced to evidence, uncertainty stays visible, and the officer decides what to publish. Built for challenge **C08** ([brief](docs/C08_BRIEF.md)).

**Promise demonstrated:** mixed evidence → an evidence-backed draft that surfaces conflicts and holds unsupported numbers, with a human approval gate and a downloadable PDF.
**Still a hypothesis:** real ingestion pipeline, multi-user roles, production hosting.

---

## Run it

```bash
cp .env.example .env        # fill DEEPSEEK_API_KEY (or set AGENT_MODE=mock to run with no key)
docker compose up -d --build
```

- Console: http://localhost:3000  — demo access key: **`schmitz2026`**
- API + docs: http://localhost:8000/docs

### Demo flow (repeatable start state)
1. **Events** → **+ New** creates an event from a synthetic scenario (`initial.json` / `scenarios/`).
2. Open the event → **Generate report**. The agent produces claims, each with a status
   (supported / conflicting / unsupported / uncertain), the evidence behind it, and its reasoning.
3. Click an **evidence chip** to jump to the verbatim source record at the bottom.
4. **+ Add note** on any claim; or submit a note under *Ask the agent to revise* → the agent
   re-generates and regenerates the PDF → **Accept** (kept, stored) or **Refuse** (reverts).
5. Keep/dismiss the **open questions for the partner**.
6. **Approve → PDF**. Find it under **Report history** (searchable by event name, downloadable).

To reset: `docker compose down -v` (wipes the database) then `up` again.

---

## Evidence view + uncertain/failure case
The demo scenario (`initial.json`) is the classic mixed-evidence case:
- A field update claims *"about twenty were trained and completed"*.
- The attendance sheet shows **18** attended.
- A coordinator note says completion needs an **assessment (ASSESS)** record, which has not arrived.

The agent therefore: reports **18 attended** (supported), flags **20 vs 18** as **conflicting** (holds the
unsupported number, does not pick one), and marks **completion** as **unsupported** — you cannot claim
completion from attendance. That is the uncertainty the report must not polish away.

---

## Real vs simulated
| Real | Simulated / mocked |
|---|---|
| The agent reasoning (live DeepSeek call, OpenAI-compatible) | The source reports (synthetic JSON in `scenarios/`) |
| Rule enforcement via the per-domain **context file** | The incoming-event button (`/simulate`, labeled) |
| Postgres persistence, state machine, PDF generation | Any partner "send" (none is wired to a real channel) |
| Claim → evidence links, revision accept/refuse history | The demo access key (frontend gate, not real auth) |

Context-agnostic by design: two context files ship (`schmitz_youth_digital`, `construction_concrete_pour`).
Swapping one JSON re-targets the agent to another program area — no code change.

---

## Limitations
- **Single user** (officer). No separate reviewer role yet.
- **Not hosted**: runs locally via Docker; PDFs are written to local disk (`reports_out/`).
- The agent falls back to a deterministic canned draft (`AGENT_MODE=mock`) if the model call fails —
  clearly logged, so a demo never dies mid-presentation.
- Demo key is a frontend gate, not authentication.

## Next validation test
Give the console to someone who has not seen it. Without help, can they: find where the attendance
number comes from, say why "20" is excluded, name the next question for the partner, and approve?
Anything they cannot do becomes the next fix.

---

## Wolf handoff (next integration)
- **Next integration:** replace the synthetic `initial.json` ingestion with the real report intake
  (the mock `/events/{id}/reports` endpoint is the seam).
- **Access required:** the source-report feed/credentials; a hosted Postgres (Neon); object storage
  (R2/S3) for PDFs once off local disk.
- **Owner:** Fahd (prototype). Integration owner: TBD.
- **Unresolved risk:** keyword/context rules are only as good as the context file; the agent can still
  mis-rank a claim, so the **human approval gate is load-bearing** and must stay.

---

## Stack
FastAPI · Postgres · SQLAlchemy · DeepSeek (OpenAI-compatible) · ReportLab (PDF) · Next.js · Docker Compose.
See [docs/EXECUTION_GUIDE.md](docs/EXECUTION_GUIDE.md) for architecture and endpoint details.
