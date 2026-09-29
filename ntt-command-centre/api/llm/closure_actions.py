"""
LLM-refined next steps for the Deal Closure worklist.

The rule in `semantic.storyline._closure_action` always chooses the action; the
model only rewrites that sentence so it reads as a specific instruction. The
refinement runs once in the background (one batched call for every deal), each
sentence is held to the grounding contract (no number the deal's own workbook
facts did not supply), and the accepted text is written to disk so a restart
does not spend another call. Nothing here blocks a page: until a refinement is
available, or if the language layer is off, the rule's sentence is shown.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from pathlib import Path

from config import ROOT

from . import grounding as G
from . import prompts, providers

PROMPT_VERSION = "CLOSURE_ACTIONS_V2"
CACHE_FILE = ROOT / "data" / "generated" / "closure_actions.json"
MAX_WORDS = 40
#: Deals per call. gpt-oss spends part of max_tokens on reasoning, and a batch of
#: all nineteen was cut off part-way; seven fits comfortably.
BATCH = 7
#: Groq free-tier limits are per minute; one retry after this pause usually clears.
RATE_LIMIT_WAIT_S = 45

SCHEMA = {
    "type": "object",
    "properties": {
        "actions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"id": {"type": "string"}, "text": {"type": "string"}},
                "required": ["id", "text"],
            },
        },
    },
    "required": ["actions"],
}

_lock = threading.Lock()
_refined: dict[str, str] | None = None


def signature(facts: dict[str, str], draft: str) -> str:
    """Changes whenever the deal's facts, the rule's draft or the prompt change."""
    raw = json.dumps([PROMPT_VERSION, facts, draft], sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def _load() -> dict[str, str]:
    global _refined
    if _refined is None:
        try:
            _refined = json.loads(Path(CACHE_FILE).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            _refined = {}
    return _refined


def lookup(facts: dict[str, str], draft: str) -> str | None:
    with _lock:
        return _load().get(signature(facts, draft))


def _problem(text: str, facts: dict[str, str], draft: str) -> str | None:
    """Why a refined sentence cannot be shown, or None when it can."""
    words = len(text.split())
    if not words or words > MAX_WORDS:
        return f"{words} words"
    _, bad = G.verify([{"text": text}], G.pack_figures(facts), extra=[draft])
    return f"ungrounded {bad[0]['rejectedTokens']}" if bad else None


def _message(chunk: dict[str, tuple[dict[str, str], str]]) -> str:
    evidence = [{"id": i, "facts": facts, "draft": draft} for i, (facts, draft) in chunk.items()]
    return G.render(
        {}, entities=[], evidence=evidence, charts_say=[],
        untrusted=[f"{i}: {facts['Primary driver']}" for i, (facts, _) in chunk.items()],
        task=("For each deal id in EVIDENCE, rewrite its draft action as described. "
              "The FIGURES block is empty because each deal carries its own facts; "
              "a number may only be used in the entry for the deal whose facts contain it. "
              'Respond as {"actions": [{"id": "<deal id>", "text": "<action>"}]}.'),
    )


def _entries(obj: dict) -> list[tuple[str, str]]:
    """Accept the schema's list, or the id-to-text map some providers return instead."""
    items = obj.get("actions")
    if isinstance(items, list):
        pairs = [(str(i.get("id")), i.get("text")) for i in items if isinstance(i, dict)]
    else:
        pairs = list(obj.items())
    return [(k, _plain(v)) for k, v in pairs if isinstance(v, str) and v.strip()]


#: Typographic characters gpt-oss likes (non-breaking hyphen, dashes, curly
#: quotes) mapped to the plain forms the rest of the product writes.
_TYPOGRAPHY = str.maketrans({"‑": "-", "‐": "-", "–": "-", "—": "-",
                             "‘": "'", "’": "'", "“": '"', "”": '"',
                             " ": " ", " ": " "})


def _plain(text: str) -> str:
    return " ".join(text.translate(_TYPOGRAPHY).split())


def refine(deals: list[tuple[dict[str, str], str]]) -> dict:
    """Refine every deal whose current signature has no accepted sentence yet."""
    with _lock:
        cache = dict(_load())
    todo = {f"D{i}": (facts, draft) for i, (facts, draft) in enumerate(deals)
            if signature(facts, draft) not in cache}
    if not todo:
        return {"requested": 0, "accepted": 0}

    accepted, rejected, meta = 0, [], {}
    ids = list(todo)
    for batch in (ids[i:i + BATCH] for i in range(0, len(ids), BATCH)):
        chunk = {i: todo[i] for i in batch}
        res = None
        for attempt in range(2):
            try:
                res = providers.complete(prompts.CLOSURE_ACTIONS_V2, _message(chunk), SCHEMA,
                                         max_tokens=3000, temperature=0.3, deadline_s=40)
                break
            except providers.LLMUnavailable as e:
                meta["error"] = str(e)
                if attempt == 0 and "busy" in str(e):
                    time.sleep(RATE_LIMIT_WAIT_S)  # background job: waiting costs nobody
        if res is None:
            continue
        meta.update(provider=res.provider, model=res.model)
        meta.pop("error", None)
        for deal_id, text in _entries(res.obj):
            deal = chunk.get(deal_id)
            if not deal:
                continue
            problem = _problem(text, *deal)
            if problem:
                rejected.append({"id": deal_id, "reason": problem, "text": text})
            else:
                cache[signature(*deal)] = text
                accepted += 1
    with _lock:
        global _refined
        # Another process (a reloaded dev server, a second worker) may have saved
        # refinements meanwhile; merge rather than overwrite them.
        try:
            on_disk = json.loads(Path(CACHE_FILE).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            on_disk = {}
        _refined = {**on_disk, **cache}
        try:
            CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            CACHE_FILE.write_text(json.dumps(_refined, indent=1, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass
    return {"requested": len(todo), "accepted": accepted, "rejected": rejected, **meta}
