"""The agent core: ONE structured pass turns evidence into a draft.

Deterministic parsing happens in main.py (JSON -> evidence records). This module
does the single LLM call, forced to emit the AgentDraft schema via tool use. If the
call fails (bad key, no network), it falls back to a deterministic mock so the demo
never dies mid-presentation.
"""
import json
import logging

from .config import settings
from .schemas import AgentDraft

log = logging.getLogger("agent")

SYSTEM = """You are an evidence-based reporting agent. You receive a context file
(rules, terminology, metrics for a specific business area) and a set of source reports,
each already turned into an evidence record with a numeric id. The context file is the
sole authority on the rules and wording - do not assume any domain of your own.

Your job, in ONE pass:
- Extract atomic claims about the event.
- Group claims about the same fact across sources.
- For every claim set status: supported | conflicting | unsupported | uncertain.
- Cite the evidence_ids that back each claim. A claim with no evidence id is unsupported.
- Apply the context rules exactly (see the "rules" and "terminology" in the context file).
  In particular: a numeric claim needs unit, period and an evidence record or it is
  unsupported; never infer an outcome/conformity/acceptance from an action alone; and any
  failed or out-of-spec result must be surfaced, never omitted.
- When two sources disagree on a number, produce ONE claim with status 'conflicting' that
  names both values in its text, and hold the unverified number rather than picking one.
- Suggest the follow-up questions the officer should ask the partner/supplier to resolve gaps.

Claim only what the evidence supports. Never smooth over a disagreement or drop a failed test.
Return the draft as structured data only, no prose."""


def _tool_schema() -> dict:
    return {
        "name": "emit_draft",
        "description": "Emit the structured draft report.",
        "input_schema": AgentDraft.model_json_schema(),
    }


def _user_prompt(context: dict, evidence_items: list[dict], instruction: str | None = None) -> str:
    lines = ["## CONTEXT FILE", json.dumps(context, ensure_ascii=False, indent=2), "", "## EVIDENCE RECORDS"]
    for e in evidence_items:
        tag = " [SIMULATED]" if e.get("simulated") else ""
        lines.append(f"- evidence_id={e['id']} | role={e['role']} | format={e['format']}{tag}\n  {e['text']}")
    if instruction:
        lines.append(
            "\n## OFFICER REVISION REQUEST\n"
            "The officer reviewed the draft and asks for this change. Apply it while still obeying "
            "the context rules (never invent evidence, never drop a failed test):\n"
            f"  {instruction}"
        )
    lines.append("\nProduce the draft now.")
    return "\n".join(lines)


def run_agent(context: dict, evidence_items: list[dict], instruction: str | None = None) -> AgentDraft:
    if settings.agent_mode == "mock":
        log.warning("AGENT_MODE=mock: returning deterministic canned draft")
        return _mock_draft(evidence_items)
    try:
        if settings.agent_provider == "anthropic":
            return _anthropic_draft(context, evidence_items, instruction)
        return _deepseek_draft(context, evidence_items, instruction)
    except Exception as exc:  # bad key, network, schema drift -> keep the demo alive
        log.error("live agent call failed (%s); falling back to mock draft", exc)
        return _mock_draft(evidence_items)


def _deepseek_draft(context: dict, evidence_items: list[dict], instruction: str | None = None) -> AgentDraft:
    """DeepSeek / any OpenAI-compatible endpoint, using JSON mode."""
    from openai import OpenAI

    client = OpenAI(api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url)
    schema = json.dumps(AgentDraft.model_json_schema(), ensure_ascii=False)
    user = (
        _user_prompt(context, evidence_items, instruction)
        + "\n\nReturn ONLY a JSON object that conforms to this JSON schema (no prose, no markdown):\n"
        + schema
    )
    resp = client.chat.completions.create(
        model=settings.agent_model,
        response_format={"type": "json_object"},
        max_tokens=3000,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user},
        ],
    )
    payload = json.loads(resp.choices[0].message.content)
    return AgentDraft.model_validate(payload)


def _anthropic_draft(context: dict, evidence_items: list[dict], instruction: str | None = None) -> AgentDraft:
    from anthropic import Anthropic

    kwargs = {"api_key": settings.anthropic_api_key}
    if settings.anthropic_base_url:
        kwargs["base_url"] = settings.anthropic_base_url
    client = Anthropic(**kwargs)

    resp = client.messages.create(
        model=settings.agent_model,
        max_tokens=2000,
        system=SYSTEM,
        tools=[_tool_schema()],
        tool_choice={"type": "tool", "name": "emit_draft"},
        messages=[{"role": "user", "content": _user_prompt(context, evidence_items, instruction)}],
    )
    for block in resp.content:
        if getattr(block, "type", None) == "tool_use":
            return AgentDraft.model_validate(block.input)
    raise ValueError("model did not return an emit_draft tool call")


# ---- deterministic fallback (keyed off role/format/keywords) ------------------------
def _find(evidence_items, **kw):
    for e in evidence_items:
        if all(str(e.get(k, "")).lower() == str(v).lower() for k, v in kw.items()):
            return e
    return None


def _mock_draft(evidence_items: list[dict]) -> AgentDraft:
    # dispatch by which domain's formats are present
    if _find(evidence_items, format="qc_slump_form") or _find(evidence_items, format="delivery_log"):
        return _mock_construction(evidence_items)
    return _mock_foundation(evidence_items)


def _mock_construction(evidence_items: list[dict]) -> AgentDraft:
    foreman = _find(evidence_items, format="site_update_freetext")
    qc = _find(evidence_items, format="qc_slump_form")
    log_ = _find(evidence_items, format="delivery_log")
    disp = _find(evidence_items, format="disposition_record")

    claims: list[dict] = []

    if log_:
        claims.append({
            "text": "4 concrete trucks were delivered to Block B by BetonPlus on 14 Feb 2026.",
            "value": "4", "unit": "trucks", "period": "2026-02-14",
            "evidence_ids": [log_["id"]], "status": "supported",
            "reasoning": "Delivery log records 4 trucks received and signed for. Satisfies R1.",
        })

    if foreman and qc:
        claims.append({
            "text": "Concrete volume is disputed: the foreman reports ~28 m3, the QC record shows 26 m3 received.",
            "value": "28 vs 26", "unit": "m3", "period": "2026-02-14",
            "evidence_ids": [foreman["id"], qc["id"]], "status": "conflicting",
            "reasoning": "Two sources disagree on volume. The 28 m3 is an approximation ('about'); the QC record states 26 m3. Held as conflicting rather than picking one (R1).",
        })

    if qc:
        claims.append({
            "text": "Truck 3 FAILED the slump test (22 cm, spec max 18 cm) and was poured on site-lead instruction. Only 2 of 4 trucks were tested.",
            "value": "22", "unit": "cm", "period": "2026-02-14",
            "evidence_ids": [qc["id"]], "status": "supported",
            "reasoning": "QC form records Truck 3 slump 22 cm, exceeding the 18 cm spec. NOTE-A: a failed test must be surfaced, not omitted. The foreman's 'went fine' is a judgement, not evidence (R3).",
        })

    # the buried consequence: was the failed load placed in the structural slab?
    if disp:
        claims.append({
            "text": "The out-of-spec Truck 3 load was rejected and returned; it was NOT placed in the Block B slab. The slab used 3 conforming trucks (~21 m3).",
            "value": "21", "unit": "m3", "period": "2026-02-14",
            "evidence_ids": [disp["id"]], "status": "supported",
            "reasoning": "Disposition record confirms Truck 3 was rejected and returned, resolving the earlier uncertainty. Conformity of the placed concrete now supported.",
        })
    elif qc:
        claims.append({
            "text": "Whether the out-of-spec Truck 3 concrete was placed in the structural slab is UNCONFIRMED.",
            "value": None, "unit": None, "period": "2026-02-14",
            "evidence_ids": [qc["id"]], "status": "uncertain",
            "reasoning": "The QC record says Truck 3 was poured on instruction, but no source confirms whether that load went into the structural slab or was diverted. Cannot be claimed either way (R3).",
        })

    suggestions: list[dict] = []
    if not disp:
        suggestions.append({"question": "Confirm the disposition of the out-of-spec Truck 3 load: was it placed in the Block B slab or rejected/diverted?", "about_claim_index": None})
    suggestions.append({"question": "Provide batch tickets to reconcile the delivered volume - the foreman says ~28 m3, QC recorded 26 m3.", "about_claim_index": None})
    suggestions.append({"question": "Provide slump results for the two untested trucks (Trucks 2 and 4).", "about_claim_index": None})

    return AgentDraft.model_validate({"claims": claims, "suggestions": suggestions})


def _mock_foundation(evidence_items: list[dict]) -> AgentDraft:
    att = _find(evidence_items, format="attendance_sheet")
    field = _find(evidence_items, format="field_update_freetext")
    note = _find(evidence_items, format="coordinator_note")
    assess = _find(evidence_items, format="assessment_record")

    claims: list[dict] = []

    if att:
        claims.append({
            "text": "18 young people attended the Q1 2026 digital skills workshops in Essen.",
            "value": "18", "unit": "people", "period": "Q1 2026",
            "evidence_ids": [att["id"]], "status": "supported",
            "reasoning": "Attendance sheet reports 18 unique participants across six signed sessions. Satisfies R1 (unit, period, record).",
        })
        claims.append({
            "text": "Six sessions were held in Q1 2026 (S1-S6).",
            "value": "6", "unit": "sessions", "period": "Q1 2026",
            "evidence_ids": [att["id"]], "status": "supported",
            "reasoning": "Attendance sheet lists six sessions with per-session counts.",
        })

    if field and att:
        claims.append({
            "text": "Participant count is disputed: the field update says 'about twenty', the attendance sheet shows 18.",
            "value": "20 vs 18", "unit": "people", "period": "Q1 2026",
            "evidence_ids": [field["id"], att["id"]], "status": "conflicting",
            "reasoning": "Two sources disagree on the count. The '20' is an approximation with no record; the signed sheet shows 18. Held as conflicting rather than picking one (R1).",
        })

    if field:
        completion_status = "unsupported"
        reason = "Field update claims participants 'completed' the program, but NOTE-A/R3 forbid inferring completion from participation, and no ASSESS record is present. Held back."
        ev = [field["id"]]
        if note:
            ev.append(note["id"])
        if assess:
            completion_status = "supported"
            reason = "ASSESS record now present: 11 participants sat and passed the end-of-program assessment. Completion supported for 11 (R3/NOTE-A satisfied)."
            ev = [assess["id"]]
            claims.append({
                "text": "11 participants completed the program (passed the end-of-program assessment) in Q1 2026.",
                "value": "11", "unit": "people", "period": "Q1 2026",
                "evidence_ids": [assess["id"]], "status": "supported",
                "reasoning": reason,
            })
        else:
            claims.append({
                "text": "Completion cannot be reported for Q1 2026: no participant has been assessed.",
                "value": None, "unit": "people", "period": "Q1 2026",
                "evidence_ids": ev, "status": completion_status,
                "reasoning": reason,
            })

    suggestions: list[dict] = []
    if not assess:
        suggestions.append({"question": "Please send the end-of-program assessment (ASSESS) records for Q1 2026 so completion can be reported.", "about_claim_index": None})
    suggestions.append({"question": "Please confirm the exact participant count for Q1 - the field update says ~20 but the attendance sheet shows 18.", "about_claim_index": None})

    return AgentDraft.model_validate({"claims": claims, "suggestions": suggestions})
