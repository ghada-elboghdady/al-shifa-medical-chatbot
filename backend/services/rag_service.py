"""
RAG Service — loads hospital data and provides retrieval using BM25-style
keyword search. No embedding API calls needed, works with any API key.
Results are injected as context into the LLM prompt.
"""

import json
import re
from pathlib import Path
from typing import List, Tuple

# Paths
DATA_PATH = Path(__file__).parent.parent.parent / "data" / "hospital_data.json"

# In-memory store
_documents: List[str] = []
_metadatas: List[dict] = []
_hospital_data: dict = None


# ── Document builder ───────────────────────────────────────────────────────

def _build_documents(data: dict) -> Tuple[List[str], List[dict]]:
    """Convert hospital JSON into searchable text chunks."""
    docs, metas = [], []

    group = data["hospital_group"]

    # Hospital overview (EN)
    docs.append(
        f"{group['name']} ({group['name_ar']}) is a hospital group "
        f"with branches in Cairo, Alexandria, Riyadh, and Dubai. "
        f"Hotline: {group['hotline']}. {group['description']}"
    )
    metas.append({"type": "hospital_info"})

    # Hospital overview (AR)
    docs.append(
        f"مجموعة الشفاء الطبية لديها فروع في القاهرة والإسكندرية والرياض ودبي. "
        f"خط الطوارئ: {group['hotline']}. {group['description_ar']}"
    )
    metas.append({"type": "hospital_info"})

    # Branch documents
    for branch in data["branches"]:
        specs = ", ".join(branch["specializations"])
        docs.append(
            f"Al Shifa Medical Group - {branch['name']} Branch is in {branch['city']}, {branch['country']}. "
            f"Address: {branch['address']}. Phone: {branch['phone']}. "
            f"Available specializations at {branch['name']}: {specs}."
        )
        metas.append({
            "type": "branch",
            "branch_id": branch["id"],
            "branch": branch["name"],
            "city": branch["city"],
        })
        docs.append(
            f"فرع مجموعة الشفاء الطبية في {branch['name_ar']} يقع في {branch['city']}. "
            f"التخصصات المتاحة في {branch['name_ar']}: {specs}."
        )
        metas.append({
            "type": "branch",
            "branch_id": branch["id"],
            "branch": branch["name"],
            "city": branch["city"],
        })

    # Doctor documents
    for doctor in data["doctors"]:
        langs = ", ".join(doctor["languages"])
        docs.append(
            f"Doctor {doctor['name']} ({doctor['name_ar']}) is a {doctor['specialty']} specialist "
            f"at Al Shifa Medical Group, {doctor['branch']} branch. "
            f"Experience: {doctor['experience_years']} years. "
            f"Languages spoken: {langs}. "
            f"Bio: {doctor['bio']}"
        )
        metas.append({
            "type": "doctor",
            "doctor_id": doctor["id"],
            "doctor_name": doctor["name"],
            "specialty": doctor["specialty"],
            "branch": doctor["branch"],
            "branch_id": doctor["branch_id"],
        })
        docs.append(
            f"الطبيب/ة {doctor['name_ar']} متخصص/ة في {doctor['specialty']} "
            f"في فرع {doctor['branch']} لمجموعة الشفاء الطبية. "
            f"خبرة: {doctor['experience_years']} سنوات."
        )
        metas.append({
            "type": "doctor",
            "doctor_id": doctor["id"],
            "doctor_name": doctor["name"],
            "specialty": doctor["specialty"],
            "branch": doctor["branch"],
            "branch_id": doctor["branch_id"],
        })

    return docs, metas


# ── Keyword retrieval ──────────────────────────────────────────────────────

def _tokenize(text: str) -> List[str]:
    """Simple tokenizer: lowercase, split on non-alphanumeric."""
    return re.findall(r"[a-zA-Z\u0600-\u06FF]+", text.lower())


def _score(query_tokens: List[str], doc: str) -> float:
    """Score a document by counting how many query tokens appear in it."""
    doc_lower = doc.lower()
    score = 0.0
    for token in query_tokens:
        if token in doc_lower:
            score += 1.0
            # Bonus for exact word match
            if re.search(r"\b" + re.escape(token) + r"\b", doc_lower):
                score += 0.5
    return score


def retrieve(query: str, n_results: int = 8) -> str:
    """Retrieve top-n most relevant hospital documents for the query."""
    if not _documents:
        return ""

    query_tokens = _tokenize(query)
    if not query_tokens:
        return ""

    scores = [(_score(query_tokens, doc), i) for i, doc in enumerate(_documents)]
    scores.sort(key=lambda x: x[0], reverse=True)

    # Take top results with score > 0
    top_docs = [
        _documents[i]
        for score, i in scores[:n_results]
        if score > 0
    ]

    if not top_docs:
        # Fall back to returning first few docs as general context
        top_docs = _documents[:4]

    return "\n\n".join(top_docs)


# ── Public API ─────────────────────────────────────────────────────────────

def initialize():
    """Initialize the RAG service."""
    global _documents, _metadatas, _hospital_data

    print("[RAG] Loading hospital data...")
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        _hospital_data = json.load(f)

    print("[RAG] Building document corpus...")
    _documents, _metadatas = _build_documents(_hospital_data)
    print(f"[RAG] Ready ({len(_documents)} documents indexed with keyword search).")


def get_hospital_data() -> dict:
    return _hospital_data or {}
