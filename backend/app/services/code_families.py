"""Synthesizes thematic "code families" from a research question's filed memo entries — a
precursor to a future codebook/tagging system, not a replacement for one (per
docs/prd-phase-2.md: assigning codes to individual highlights/snippets stays out of scope
this round). Same human-in-the-loop posture as ai_review.py and next_steps.py: the model
proposes family definitions grounded in the user's own already-accepted/edited insights;
nothing is "decided" until the user accepts, renames, or dismisses.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from openai import OpenAI
from sqlalchemy.orm import Session

from ..config import CodeFamiliesConfig, Config
from ..evidence_text import quoted_texts
from ..models_prototype import CodeFamily, CodeFamilyMember, CodeFamilyMergeSuggestion, ReflectionConnection

FILED_STATUSES = ("accepted", "edited")
# Families that count toward the per-RQ cap and that the model may attach to or merge.
LIVE_FAMILY_STATUSES = ("suggested", "accepted")

CODE_FAMILY_PROMPT = """You help a sensemaker build a first-draft codebook from their own \
already-filed research insights, one research question (RQ) at a time.

You are given every accepted/edited memo entry under this RQ (insight text plus the evidence \
passages behind it), any thematic clusters ("code families") already proposed or accepted \
for this RQ, and limits on how many new families you may propose this run.

Code families are broad parent themes: later, finer-grained child codes will sit underneath \
them. Keep them few and wide. Each one should name a major topic or broad stroke of the RQ, \
not a specific nuance, sub-point, or single anecdote within a topic.

Rules:
- A family's definition must be grounded in the actual insight text/evidence you were given — \
don't invent a theme the entries don't support.
- Every value in member_connection_ids must be one of the connection ids you were actually \
given — never invent one.
- Strongly prefer attaching entries to an existing family (reference its existing_family_id) \
over proposing a new one. If a new entry is a nuance of an existing broad theme, it belongs \
in that existing family. Only create a new family for a genuinely distinct broad theme.
- Propose at most max_new_families families with existing_family_id = null. If that is 0, \
only attach entries to existing families.
- This produces family *definitions* only — never propose assigning codes to individual \
highlights or snippets; that stays out of scope.
- It's fine to leave entries out of every family if they don't cluster with anything yet, and \
fine to return an empty families list if nothing genuinely clusters.
- merge_suggestions: only when propose_merges is true. Suggest merging two or more existing \
families (by id) whose themes overlap or that are really facets of one broader theme, with a \
proposed broader name and definition and a one-sentence rationale grounded in the families' \
definitions and member entries. Suggest nothing if no merge is genuinely warranted. When \
propose_merges is false, return an empty merge_suggestions list.
"""

_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "families": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "existing_family_id": {"type": ["integer", "null"]},
                    "name": {"type": ["string", "null"]},
                    "definition": {"type": ["string", "null"]},
                    "member_connection_ids": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["existing_family_id", "name", "definition", "member_connection_ids"],
                "additionalProperties": False,
            },
        },
        "merge_suggestions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "family_ids": {"type": "array", "items": {"type": "integer"}},
                    "name": {"type": "string"},
                    "definition": {"type": "string"},
                    "rationale": {"type": "string"},
                },
                "required": ["family_ids", "name", "definition", "rationale"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["families", "merge_suggestions"],
    "additionalProperties": False,
}


def _filed_connections_for_rq(prototype_db: Session, research_question_id: int) -> list[ReflectionConnection]:
    return (
        prototype_db.query(ReflectionConnection)
        .filter(
            ReflectionConnection.research_question_id == research_question_id,
            ReflectionConnection.status.in_(FILED_STATUSES),
        )
        .all()
    )


def _valid_connection_ids(prototype_db: Session, research_question_id: int) -> set[int]:
    """Every member_connection_id the model proposes must resolve to one of these before
    it's trusted — mirrors next_steps._valid_conversation_ids."""
    rows = (
        prototype_db.query(ReflectionConnection.id)
        .filter(
            ReflectionConnection.research_question_id == research_question_id,
            ReflectionConnection.status.in_(FILED_STATUSES),
        )
        .all()
    )
    return {row.id for row in rows}


def _connection_context(cortico_db: Session, connections: list[ReflectionConnection]) -> list[dict]:
    spans = [(e.snippet_id, e.start_index, e.end_index) for c in connections for e in c.evidence]
    text_by_span = quoted_texts(cortico_db, spans)
    return [
        {
            "connection_id": c.id,
            "insight_text": c.insight_text,
            "evidence": [text_by_span.get((e.snippet_id, e.start_index, e.end_index), "") for e in c.evidence],
        }
        for c in connections
    ]


def _existing_families_context(
    prototype_db: Session, research_question_id: int
) -> tuple[list[CodeFamily], list[dict]]:
    families = (
        prototype_db.query(CodeFamily)
        .filter(
            CodeFamily.research_question_id == research_question_id,
            CodeFamily.status.in_(LIVE_FAMILY_STATUSES),
        )
        .all()
    )
    return families, [
        {
            "id": f.id,
            "name": f.name,
            "definition": f.definition,
            "member_connection_ids": [m.connection_id for m in f.members],
        }
        for f in families
    ]


def _apply_family_results(
    prototype_db: Session,
    *,
    research_question_id: int,
    user_id: int,
    raw_families: list[dict],
    valid_connection_ids: set[int],
    existing_family_ids: set[int],
    ai_metadata: dict,
    max_new: int | None = None,
) -> tuple[list[CodeFamily], int]:
    """Returns (touched families, number of new families withheld by the cap). max_new=None
    means uncapped."""
    touched: list[CodeFamily] = []
    created = 0
    withheld = 0
    for fam in raw_families:
        member_ids = [cid for cid in fam.get("member_connection_ids", []) if cid in valid_connection_ids]
        if not member_ids:
            continue  # nothing real left to attach for this candidate

        target: CodeFamily | None = None
        existing_id = fam.get("existing_family_id")
        if existing_id is not None and existing_id in existing_family_ids:
            target = prototype_db.get(CodeFamily, existing_id)

        if target is None:
            name = fam.get("name")
            definition = fam.get("definition")
            if not name or not definition:
                continue  # no existing family matched and nothing coherent to create
            if max_new is not None and created >= max_new:
                withheld += 1  # enforced here too, not just asked of the model
                continue
            created += 1
            target = CodeFamily(
                user_id=user_id,
                research_question_id=research_question_id,
                name=name,
                definition=definition,
                status="suggested",
                ai_metadata=json.dumps(ai_metadata),
            )
            prototype_db.add(target)
            prototype_db.flush()  # assign target.id

        existing_member_ids = {m.connection_id for m in target.members}
        for cid in member_ids:
            if cid not in existing_member_ids:
                prototype_db.add(CodeFamilyMember(code_family_id=target.id, connection_id=cid))
                existing_member_ids.add(cid)

        touched.append(target)

    prototype_db.commit()
    return touched, withheld


def _apply_merge_suggestions(
    prototype_db: Session,
    *,
    research_question_id: int,
    user_id: int,
    raw_merges: list[dict],
    live_family_ids: set[int],
    ai_metadata: dict,
) -> list[CodeFamilyMergeSuggestion]:
    """Persists merge suggestions whose family ids all resolve to this RQ's live families.
    Skips any whose exact family set already has a pending suggestion, so re-running
    synthesis near the cap doesn't stack up duplicates."""
    pending_sets = {
        frozenset(json.loads(m.family_ids_json))
        for m in prototype_db.query(CodeFamilyMergeSuggestion).filter(
            CodeFamilyMergeSuggestion.research_question_id == research_question_id,
            CodeFamilyMergeSuggestion.status == "suggested",
        )
    }
    created: list[CodeFamilyMergeSuggestion] = []
    for merge in raw_merges:
        ids = list(dict.fromkeys(fid for fid in merge.get("family_ids", []) if fid in live_family_ids))
        if len(ids) < 2 or not merge.get("name") or not merge.get("definition"):
            continue
        if frozenset(ids) in pending_sets:
            continue
        pending_sets.add(frozenset(ids))
        suggestion = CodeFamilyMergeSuggestion(
            user_id=user_id,
            research_question_id=research_question_id,
            family_ids_json=json.dumps(ids),
            target_family_id=_merge_target(prototype_db, ids),
            proposed_name=merge["name"],
            proposed_definition=merge["definition"],
            rationale=merge.get("rationale"),
            status="suggested",
            ai_metadata=json.dumps(ai_metadata),
        )
        prototype_db.add(suggestion)
        created.append(suggestion)
    prototype_db.commit()
    return created


def _merge_target(prototype_db: Session, family_ids: list[int]) -> int:
    """The family that survives a merge: prefer one the user already accepted, then the
    oldest, so accepted work keeps its id."""
    families = prototype_db.query(CodeFamily).filter(CodeFamily.id.in_(family_ids)).all()
    families.sort(key=lambda f: (f.status != "accepted", f.created_at, f.id))
    return families[0].id


def accept_merge(prototype_db: Session, suggestion: CodeFamilyMergeSuggestion) -> CodeFamily:
    """Folds every source family's members into the target, renames the target to the
    proposed name/definition, and marks the other sources "merged" (kept, not deleted).
    Re-checks that every source family is still live, since the user may have dismissed one
    since the suggestion was made."""
    family_ids = json.loads(suggestion.family_ids_json)
    families = {f.id: f for f in prototype_db.query(CodeFamily).filter(CodeFamily.id.in_(family_ids))}
    if any(families.get(fid) is None or families[fid].status not in LIVE_FAMILY_STATUSES for fid in family_ids):
        raise ValueError("one of the families in this merge is no longer active")

    target = families[suggestion.target_family_id]
    member_ids = {m.connection_id for m in target.members}
    for fid in family_ids:
        if fid == target.id:
            continue
        source = families[fid]
        for m in source.members:
            if m.connection_id not in member_ids:
                prototype_db.add(CodeFamilyMember(code_family_id=target.id, connection_id=m.connection_id))
                member_ids.add(m.connection_id)
        source.status = "merged"

    target.name = suggestion.proposed_name
    target.definition = suggestion.proposed_definition
    target.status = "accepted"  # accepting the merge is the user deciding on this family
    suggestion.status = "accepted"
    prototype_db.commit()
    prototype_db.refresh(target)
    return target


@dataclass
class CapStatus:
    live_count: int
    max_per_rq: int
    near_cap: bool
    max_new_this_run: int


def cap_status(live_count: int, limits: CodeFamiliesConfig, override_cap: bool) -> CapStatus:
    room = limits.max_new_per_run if override_cap else max(0, limits.max_per_rq - live_count)
    return CapStatus(
        live_count=live_count,
        max_per_rq=limits.max_per_rq,
        near_cap=live_count >= limits.near_cap_at,
        max_new_this_run=min(limits.max_new_per_run, room),
    )


@dataclass
class SynthesisResult:
    families: list[CodeFamily]
    merge_suggestions: list[CodeFamilyMergeSuggestion] = field(default_factory=list)
    withheld_new_families: int = 0
    cap: CapStatus | None = None


def synthesize_code_families(
    *,
    prototype_db: Session,
    cortico_db: Session,
    config: Config,
    user_id: int,
    research_question_id: int,
    override_cap: bool = False,
) -> SynthesisResult:
    existing_families, existing_context = _existing_families_context(prototype_db, research_question_id)
    cap = cap_status(len(existing_families), config.code_families, override_cap)

    connections = _filed_connections_for_rq(prototype_db, research_question_id)
    if not connections:
        # nothing filed yet under this RQ — don't spend a call synthesizing nothing
        return SynthesisResult(families=[], cap=cap)

    payload = {
        "memo_entries": _connection_context(cortico_db, connections),
        "existing_code_families": existing_context,
        "max_new_families": cap.max_new_this_run,
        "propose_merges": cap.near_cap,
    }

    client = OpenAI()
    response = client.responses.create(
        model=config.ai_review.model,
        reasoning={"effort": config.ai_review.reasoning_effort},
        input=[
            {"role": "system", "content": CODE_FAMILY_PROMPT},
            {"role": "user", "content": json.dumps(payload)},
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "code_families",
                "schema": _OUTPUT_SCHEMA,
                "strict": True,
            }
        },
    )
    result = json.loads(response.output_text)
    ai_metadata = {
        "model": config.ai_review.model,
        "reasoning_effort": config.ai_review.reasoning_effort,
        "prompt": CODE_FAMILY_PROMPT,
        "override_cap": override_cap,
    }
    existing_family_ids = {f.id for f in existing_families}

    touched, withheld = _apply_family_results(
        prototype_db,
        research_question_id=research_question_id,
        user_id=user_id,
        raw_families=result.get("families", []),
        valid_connection_ids=_valid_connection_ids(prototype_db, research_question_id),
        existing_family_ids=existing_family_ids,
        ai_metadata=ai_metadata,
        max_new=cap.max_new_this_run,
    )
    merges = (
        _apply_merge_suggestions(
            prototype_db,
            research_question_id=research_question_id,
            user_id=user_id,
            raw_merges=result.get("merge_suggestions", []),
            live_family_ids=existing_family_ids,
            ai_metadata=ai_metadata,
        )
        if cap.near_cap
        else []
    )
    return SynthesisResult(families=touched, merge_suggestions=merges, withheld_new_families=withheld, cap=cap)
