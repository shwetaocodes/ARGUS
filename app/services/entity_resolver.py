"""
Hybrid entity resolution pipeline.

Priority order, each stage only runs if the previous one didn't resolve:
  1. Normalize            — deterministic, always applied first
  2. Alias dictionary      — deterministic, exact lookup, AUTO-MERGES
  3. Existing entity match — deterministic, exact name/alias lookup, AUTO-MERGES
  4. Embedding similarity  — probabilistic. High threshold AUTO-MERGES,
                              medium threshold logs a MergeCandidate, never guesses.
  5. Fuzzy matching        — probabilistic, same rule as embeddings.
  6. Create new entity     — nothing matched at any stage.

Every resolution, regardless of which stage handled it, writes one row to
EntityResolutionLog — this is what makes the pipeline auditable rather than
just "probably working."
"""

import re
import unicodedata
import numpy as np
from rapidfuzz import fuzz
from sentence_transformers import SentenceTransformer
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.entity import Entity, EntityType
from app.models.entity_alias_dictionary import EntityAliasDictionary
from app.models.entity_merge_candidate import EntityMergeCandidate
from app.models.entity_resolution_log import EntityResolutionLog

EMBEDDING_AUTO_MERGE_THRESHOLD = 0.92
EMBEDDING_REVIEW_THRESHOLD = 0.78
FUZZY_AUTO_MERGE_THRESHOLD = 96   
FUZZY_REVIEW_THRESHOLD = 85

_embedding_model = None
_CJK_RANGE = re.compile(r'[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]') 


def get_embedding_model() -> SentenceTransformer:
    """Multilingual model — this is the actual mechanism that lets 'PLA' and
    '中国人民解放军' land close together in vector space, unlike the English-only
    all-MiniLM-L6-v2 used elsewhere in this project for the cross-source correlator."""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    return _embedding_model


def normalize_name(name: str) -> str:
    """
    Stage 1. Deterministic, always applied.
    - Unicode NFKC normalization: collapses visually-identical but differently-encoded
      characters (full-width vs half-width, combining characters, etc.) to one form.
    - Latin-script text: lowercased, punctuation stripped, whitespace collapsed —
      "P.L.A." and "pla" and "PLA " all normalize to "pla".
    - CJK/other scripts: NFKC + whitespace collapse only — lowercasing has no meaning
      for Chinese characters, and stripping "punctuation" risks stripping meaningful text.
    """
    name = unicodedata.normalize("NFKC", name).strip()

    if _CJK_RANGE.search(name):
        return re.sub(r'\s+', ' ', name)

    name = name.lower()
    name = re.sub(r'[^\w\s]', '', name)  
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def _log_resolution(db: Session, input_name: str, normalized: str, entity_id: int | None, method: str, score: float | None):
    db.add(EntityResolutionLog(
        input_name=input_name, normalized_name=normalized,
        resolved_entity_id=entity_id, method=method, score=score,
    ))


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    a, b = np.array(a), np.array(b)
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    return float(np.dot(a, b) / denom) if denom > 0 else 0.0


def resolve_entity(db: Session, name: str, entity_type: str) -> Entity:
    """
    The single entry point. Returns an Entity — either an existing one that
    was matched, or a newly created one. Every call writes exactly one
    EntityResolutionLog row explaining which stage decided the outcome.
    """
    normalized = normalize_name(name)

    alias_row = db.query(EntityAliasDictionary).filter(
        EntityAliasDictionary.alias_normalized == normalized
    ).first()

    if alias_row:
        canonical_normalized = normalize_name(alias_row.canonical_name)
        entity = db.query(Entity).filter(
            Entity.type == EntityType(entity_type),
            or_(
                Entity.name.ilike(alias_row.canonical_name),
                Entity.aliases.any(alias_row.canonical_name),
            ),
        ).first()

        if entity:
            if name not in (entity.aliases or []):
                entity.aliases = (entity.aliases or []) + [name]
            _log_resolution(db, name, normalized, entity.id, "alias_dictionary", 1.0)
            return entity

        entity = Entity(name=alias_row.canonical_name, type=EntityType(entity_type), aliases=[name])
        db.add(entity)
        db.flush()
        _log_resolution(db, name, normalized, entity.id, "alias_dictionary_new", 1.0)
        return entity

    entity = db.query(Entity).filter(
        Entity.type == EntityType(entity_type),
        or_(Entity.name.ilike(name), Entity.aliases.any(name)),
    ).first()

    if entity:
        _log_resolution(db, name, normalized, entity.id, "exact_match", 1.0)
        return entity

    candidates = db.query(Entity).filter(
        Entity.type == EntityType(entity_type),
        Entity.name_embedding.isnot(None),
    ).all()

    model = get_embedding_model()
    input_embedding = model.encode(name).tolist()

    best_match, best_score = None, 0.0
    for candidate in candidates:
        sim = _cosine_similarity(input_embedding, candidate.name_embedding)
        if sim > best_score:
            best_match, best_score = candidate, sim

    if best_match and best_score >= EMBEDDING_AUTO_MERGE_THRESHOLD:
        if name not in (best_match.aliases or []):
            best_match.aliases = (best_match.aliases or []) + [name]
        _log_resolution(db, name, normalized, best_match.id, "embedding_auto", best_score)
        return best_match

    fuzzy_best, fuzzy_score = None, 0
    all_same_type = db.query(Entity).filter(Entity.type == EntityType(entity_type)).all()
    for candidate in all_same_type:
        names_to_check = [candidate.name] + (candidate.aliases or [])
        for cname in names_to_check:
            score = fuzz.token_sort_ratio(normalize_name(cname), normalized)
            if score > fuzzy_score:
                fuzzy_best, fuzzy_score = candidate, score

    if fuzzy_best and fuzzy_score >= FUZZY_AUTO_MERGE_THRESHOLD:
        if name not in (fuzzy_best.aliases or []):
            fuzzy_best.aliases = (fuzzy_best.aliases or []) + [name]
        _log_resolution(db, name, normalized, fuzzy_best.id, "fuzzy_auto", fuzzy_score / 100)
        return fuzzy_best

    new_entity = Entity(name=name, type=EntityType(entity_type), aliases=[], name_embedding=input_embedding)
    db.add(new_entity)
    db.flush()

    if best_match and best_score >= EMBEDDING_REVIEW_THRESHOLD:
        db.add(EntityMergeCandidate(
            new_entity_id=new_entity.id, matched_entity_id=best_match.id,
            method="embedding", score=best_score,
        ))
    elif fuzzy_best and fuzzy_score >= FUZZY_REVIEW_THRESHOLD:
        db.add(EntityMergeCandidate(
            new_entity_id=new_entity.id, matched_entity_id=fuzzy_best.id,
            method="fuzzy", score=fuzzy_score / 100,
        ))

    _log_resolution(db, name, normalized, new_entity.id, "new_entity", None)
    return new_entity