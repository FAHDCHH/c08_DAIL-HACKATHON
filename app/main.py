import glob
import json
import os
import time

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from . import models
from .agent import run_agent
from .config import settings
from .db import Base, engine, get_db
from .pdf import build_report_pdf
from .schemas import (
    AgentDraft,
    AnnotationIn,
    AnnotationOut,
    ClaimOut,
    DraftClaim,
    DraftSuggestion,
    EvidenceOut,
    NewReportIn,
    ReportOut,
    ReviseIn,
    RevisionDecisionIn,
    SuggestionDecisionIn,
    SuggestionOut,
)

app = FastAPI(title="Evidence-Based Reporting Agent", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # demo: the console runs on localhost:3000
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup():
    Base.metadata.create_all(bind=engine)
    # idempotent column add for DBs created before 'processed' existed
    from sqlalchemy import text as _sql
    with engine.begin() as conn:
        conn.execute(_sql("ALTER TABLE source_reports ADD COLUMN IF NOT EXISTS processed boolean DEFAULT false"))


# ---- helpers -----------------------------------------------------------------------
def _load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _context_for(context_id: str) -> dict:
    path = os.path.join(settings.contexts_dir, f"{context_id}.json")
    if not os.path.exists(path):
        raise HTTPException(404, f"context '{context_id}' not found")
    return _load_json(path)


def _evidence_items(event: models.Event) -> list[dict]:
    items = []
    for sr in event.source_reports:
        for e in sr.evidence:
            items.append({
                "id": e.id, "role": sr.role, "format": sr.format,
                "text": e.excerpt, "simulated": sr.simulated == "yes",
            })
    return items


def _apply_draft(event: models.Event, draft: AgentDraft, db: Session):
    """Replace the event's claims + suggestions with a draft, reset report to draft."""
    for c in list(event.claims):
        db.delete(c)
    for s in list(event.suggestions):
        db.delete(s)
    db.flush()

    index_to_id = {}
    for i, dc in enumerate(draft.claims):
        claim = models.Claim(
            event_id=event.id, text=dc.text, value=dc.value, unit=dc.unit,
            period=dc.period, status=dc.status, reasoning=dc.reasoning,
        )
        if dc.evidence_ids:
            claim.evidence_records = (
                db.query(models.EvidenceRecord)
                .filter(models.EvidenceRecord.id.in_(dc.evidence_ids)).all()
            )
        db.add(claim)
        db.flush()
        index_to_id[i] = claim.id

    for ds in draft.suggestions:
        about = index_to_id.get(ds.about_claim_index) if ds.about_claim_index is not None else None
        db.add(models.Suggestion(event_id=event.id, question=ds.question, about_claim_id=about))

    report = event.report or models.Report(event_id=event.id)
    report.status = "draft"
    report.approved_at = None
    report.pdf_path = None
    db.add(report)
    db.flush()


def _current_as_draft(event: models.Event) -> AgentDraft:
    """Snapshot the event's current claims + suggestions as an AgentDraft (for revert)."""
    ordered = sorted(event.claims, key=lambda x: x.id)
    id_to_index = {c.id: i for i, c in enumerate(ordered)}
    claims = [
        DraftClaim(text=c.text, value=c.value, unit=c.unit, period=c.period,
                   evidence_ids=[e.id for e in c.evidence_records], status=c.status,
                   reasoning=c.reasoning)
        for c in ordered
    ]
    suggestions = [
        DraftSuggestion(question=s.question,
                        about_claim_index=id_to_index.get(s.about_claim_id) if s.about_claim_id else None)
        for s in sorted(event.suggestions, key=lambda x: x.id)
    ]
    return AgentDraft(claims=claims, suggestions=suggestions)


def _mark_parsed(event: models.Event):
    for sr in event.source_reports:
        sr.processed = True


def _generate_pdf(event: models.Event, kind: str, db: Session) -> str:
    """Build a uniquely-named PDF and record it in the history table."""
    out = _serialize(event)
    path = build_report_pdf(out, suffix=f"{kind}_{int(time.time())}")
    db.add(models.GeneratedReport(event_id=event.id, kind=kind, pdf_path=path))
    return path


def _analyze(event: models.Event, db: Session):
    context = _context_for(event.context_id)
    draft = run_agent(context, _evidence_items(event))
    _apply_draft(event, draft, db)
    _mark_parsed(event)
    db.commit()


def _serialize(event: models.Event) -> ReportOut:
    claims = [
        ClaimOut(
            id=c.id, text=c.text, value=c.value, unit=c.unit, period=c.period,
            status=c.status, reasoning=c.reasoning,
            evidence_ids=[e.id for e in c.evidence_records],
            annotations=[AnnotationOut(id=a.id, note=a.note) for a in c.annotations],
        )
        for c in sorted(event.claims, key=lambda x: x.id)
    ]
    suggestions = [
        SuggestionOut(id=s.id, question=s.question, about_claim_id=s.about_claim_id,
                      officer_validated=s.officer_validated)
        for s in sorted(event.suggestions, key=lambda x: x.id)
    ]
    evidence = []
    for sr in sorted(event.source_reports, key=lambda x: x.id):
        for e in sr.evidence:
            evidence.append(EvidenceOut(id=e.id, role=sr.role, format=sr.format,
                                        excerpt=e.excerpt, simulated=sr.simulated == "yes"))
    return ReportOut(
        event_id=event.id, title=event.title, program=event.program, period=event.period,
        status=event.report.status if event.report else "draft",
        claims=claims, suggestions=suggestions, evidence=evidence,
        pdf_path=event.report.pdf_path if event.report else None,
    )


def _get_event(event_id: int, db: Session) -> models.Event:
    ev = db.get(models.Event, event_id)
    if not ev:
        raise HTTPException(404, "event not found")
    return ev


# ---- endpoints ---------------------------------------------------------------------
@app.get("/")
def root():
    return {"service": "evidence-based reporting agent", "agent_mode": settings.agent_mode}


@app.get("/scenarios")
def list_scenarios():
    out = []
    for p in sorted(glob.glob(os.path.join(settings.scenarios_dir, "*.json"))):
        data = _load_json(p)
        out.append({"scenario_id": data["scenario_id"], "context_id": data["context_id"],
                    "title": data["event"]["title"]})
    return out


@app.get("/events")
def list_events(q: str | None = None, db: Session = Depends(get_db)):
    """All events by name, with a flag for events that have reports not yet in a report."""
    query = db.query(models.Event)
    if q:
        query = query.filter(models.Event.title.ilike(f"%{q}%"))
    out = []
    for ev in query.order_by(models.Event.id.desc()).all():
        total = len(ev.source_reports)
        new = sum(1 for sr in ev.source_reports if not sr.processed)
        out.append({
            "event_id": ev.id, "title": ev.title, "program": ev.program, "period": ev.period,
            "report_status": ev.report.status if ev.report else "none",
            "total_reports": total, "new_reports": new,
            "needs_attention": new > 0,
        })
    return out


@app.post("/events/{event_id}/reports", response_model=ReportOut)
def add_report(event_id: int, body: NewReportIn, db: Session = Depends(get_db)):
    """A new report arrives for an existing event. It is unprocessed until the officer
    regenerates (analyze), which is what flags the event as needing attention."""
    event = _get_event(event_id, db)
    sr = models.SourceReport(event_id=event.id, role=body.role, format=body.format,
                             text=body.text, simulated="yes" if body.simulated else "no",
                             processed=False)
    sr.evidence.append(models.EvidenceRecord(excerpt=body.text))
    db.add(sr)
    db.commit()
    db.refresh(event)
    return _serialize(event)


@app.get("/reports")
def report_history(q: str | None = None, db: Session = Depends(get_db)):
    """History of every agent-generated PDF, newest first, searchable by event name."""
    rows = (
        db.query(models.GeneratedReport, models.Event)
        .join(models.Event, models.GeneratedReport.event_id == models.Event.id)
    )
    if q:
        rows = rows.filter(models.Event.title.ilike(f"%{q}%"))
    rows = rows.order_by(models.GeneratedReport.id.desc()).all()
    return [
        {"generated_id": g.id, "event_id": g.event_id, "event_title": e.title,
         "kind": g.kind, "created_at": g.created_at,
         "download_url": f"/reports/{g.id}/download"}
        for g, e in rows
    ]


@app.get("/reports/{generated_id}/download")
def download_report(generated_id: int, db: Session = Depends(get_db)):
    g = db.get(models.GeneratedReport, generated_id)
    if not g or not os.path.exists(g.pdf_path):
        raise HTTPException(404, "generated report not found")
    return FileResponse(g.pdf_path, media_type="application/pdf",
                        filename=os.path.basename(g.pdf_path))


@app.post("/scenarios/{scenario_id}/load")
def load_scenario(scenario_id: str, db: Session = Depends(get_db)):
    path = os.path.join(settings.scenarios_dir, f"{scenario_id}.json")
    if not os.path.exists(path):
        raise HTTPException(404, f"scenario '{scenario_id}' not found")
    data = _load_json(path)

    event = models.Event(
        context_id=data["context_id"], program=data["event"]["program"],
        period=data["event"]["period"], title=data["event"]["title"],
    )
    db.add(event)
    db.flush()

    for r in data["reports"]:
        sr = models.SourceReport(event_id=event.id, role=r["role"], format=r["format"], text=r["text"])
        sr.evidence.append(models.EvidenceRecord(excerpt=r["text"]))
        db.add(sr)
    db.commit()
    return {"event_id": event.id, "reports_loaded": len(data["reports"])}


@app.post("/events/{event_id}/analyze", response_model=ReportOut)
def analyze(event_id: int, db: Session = Depends(get_db)):
    event = _get_event(event_id, db)
    _analyze(event, db)
    db.refresh(event)
    return _serialize(event)


@app.get("/events/{event_id}/report", response_model=ReportOut)
def get_report(event_id: int, db: Session = Depends(get_db)):
    return _serialize(_get_event(event_id, db))


@app.get("/claims/{claim_id}/evidence")
def claim_evidence(claim_id: int, db: Session = Depends(get_db)):
    claim = db.get(models.Claim, claim_id)
    if not claim:
        raise HTTPException(404, "claim not found")
    return {
        "claim_id": claim.id,
        "claim_text": claim.text,
        "status": claim.status,
        "reasoning": claim.reasoning,
        "evidence": [
            {"id": e.id, "role": e.source_report.role, "format": e.source_report.format,
             "excerpt": e.excerpt}
            for e in claim.evidence_records
        ],
    }


@app.post("/claims/{claim_id}/annotations", response_model=AnnotationOut)
def add_annotation(claim_id: int, body: AnnotationIn, db: Session = Depends(get_db)):
    claim = db.get(models.Claim, claim_id)
    if not claim:
        raise HTTPException(404, "claim not found")
    a = models.Annotation(claim_id=claim.id, note=body.note)
    db.add(a)
    db.commit()
    return AnnotationOut(id=a.id, note=a.note)


@app.post("/suggestions/{suggestion_id}/decision", response_model=SuggestionOut)
def decide_suggestion(suggestion_id: int, body: SuggestionDecisionIn, db: Session = Depends(get_db)):
    s = db.get(models.Suggestion, suggestion_id)
    if not s:
        raise HTTPException(404, "suggestion not found")
    s.officer_validated = body.decision
    db.commit()
    return SuggestionOut(id=s.id, question=s.question, about_claim_id=s.about_claim_id,
                         officer_validated=s.officer_validated)


@app.post("/events/{event_id}/approve", response_model=ReportOut)
def approve(event_id: int, db: Session = Depends(get_db)):
    from datetime import datetime, timezone

    event = _get_event(event_id, db)
    if not event.report:
        raise HTTPException(400, "run analyze first")
    pdf_path = _generate_pdf(event, "approved", db)
    event.report.status = "approved"
    event.report.approved_at = datetime.now(timezone.utc)
    event.report.pdf_path = pdf_path
    db.commit()
    db.refresh(event)
    return _serialize(event)


@app.post("/events/{event_id}/revise")
def revise(event_id: int, body: ReviseIn, db: Session = Depends(get_db)):
    """Officer submits a note asking to change claims/suggestions. The agent re-runs with
    that instruction, the PDF is regenerated immediately, and a 'proposed' revision is stored.
    The officer then accepts or refuses it."""
    event = _get_event(event_id, db)
    before = _current_as_draft(event)
    context = _context_for(event.context_id)
    new_draft = run_agent(context, _evidence_items(event), instruction=body.instruction)

    _apply_draft(event, new_draft, db)
    _mark_parsed(event)
    pdf_path = _generate_pdf(event, "revision", db)  # PDF changes on note submission
    event.report.pdf_path = pdf_path

    rev = models.Revision(
        event_id=event.id, instruction=body.instruction, status="proposed",
        before_json=before.model_dump_json(), after_json=new_draft.model_dump_json(),
        pdf_path=pdf_path,
    )
    db.add(rev)
    db.commit()
    db.refresh(event)
    return {"revision_id": rev.id, "status": "proposed", "report": _serialize(event)}


@app.post("/revisions/{revision_id}/decision")
def decide_revision(revision_id: int, body: RevisionDecisionIn, db: Session = Depends(get_db)):
    from datetime import datetime, timezone

    rev = db.get(models.Revision, revision_id)
    if not rev:
        raise HTTPException(404, "revision not found")
    if rev.status != "proposed":
        raise HTTPException(400, f"revision already {rev.status}")
    event = _get_event(rev.event_id, db)

    if body.decision == "accept":
        # keep the revised report; the accepted revision (id + details) stays in the DB
        rev.status = "accepted"
        rev.decided_at = datetime.now(timezone.utc)
    else:
        # refuse: restore the pre-revision snapshot and regenerate the PDF
        before = AgentDraft.model_validate_json(rev.before_json)
        _apply_draft(event, before, db)
        event.report.pdf_path = _generate_pdf(event, "reverted", db)
        rev.status = "refused"
        rev.decided_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(event)
    return {"revision_id": rev.id, "status": rev.status, "report": _serialize(event)}


@app.get("/events/{event_id}/revisions")
def list_revisions(event_id: int, db: Session = Depends(get_db)):
    event = _get_event(event_id, db)
    revs = db.query(models.Revision).filter(models.Revision.event_id == event.id).order_by(models.Revision.id).all()
    return [
        {"id": r.id, "instruction": r.instruction, "status": r.status,
         "pdf_path": r.pdf_path, "created_at": r.created_at, "decided_at": r.decided_at}
        for r in revs
    ]


@app.post("/events/{event_id}/simulate", response_model=ReportOut)
def simulate_followup(event_id: int, db: Session = Depends(get_db)):
    """Clearly-labeled simulated event: partner uploads the missing record.
    Adds evidence and re-runs the agent; the report drops back to draft."""
    event = _get_event(event_id, db)
    scenario_path = None
    for p in glob.glob(os.path.join(settings.scenarios_dir, "*.json")):
        if _load_json(p)["context_id"] == event.context_id:
            scenario_path = p
            break
    if not scenario_path:
        raise HTTPException(404, "no scenario with a simulated follow-up for this context")
    followup = _load_json(scenario_path).get("simulated_followup")
    if not followup:
        raise HTTPException(404, "scenario has no simulated_followup")

    sr = models.SourceReport(event_id=event.id, role=followup["role"], format=followup["format"],
                             text=followup["text"], simulated="yes")
    sr.evidence.append(models.EvidenceRecord(excerpt=followup["text"]))
    db.add(sr)
    db.commit()
    db.refresh(event)

    _analyze(event, db)
    db.refresh(event)
    return _serialize(event)
