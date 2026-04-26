"""Labeled query → expected path substring checks for the demo corpus (Benchmarks tab)."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.exceptions import CorruptIndexError
from app.services.clip_service import get_clip_service
from app.services.faiss_store import FaissStore, get_faiss_store
from app.services.search_benchmark import _search_with_media_filter

# Search enough neighbors to get a meaningful rank; cap for very large indexes.
_MAX_RANK_SCAN = 10_000

_SPECS: list[Path] = [
    Path(__file__).resolve().parents[2] / "benchmarks" / "demo_retrieval.json",
]


def _load_spec() -> dict[str, Any]:
    for p in _SPECS:
        if p.is_file():
            with open(p, encoding="utf-8") as f:
                return json.load(f)
    raise FileNotFoundError("demo_retrieval.json not found (expected under backend/benchmarks/)")


@dataclass(frozen=True)
class DemoCaseResult:
    label: str
    query: str
    path_includes: str
    expected_in_index: bool
    rank: int | None
    in_top_k: bool
    best_score: float | None
    latency_ms: float
    note: str | None


@dataclass(frozen=True)
class DemoRetrievalResult:
    ntotal: int
    top_k: int
    media_filter: str
    spec_version: int
    spec_description: str
    cases: list[DemoCaseResult]
    pass_count: int
    case_count: int
    recall: float
    search_rank_depth: int
    count_expected_in_index: int
    count_not_in_index: int


def _path_matches_sub(path: str, sub: str) -> bool:
    p = str(path).replace("\\", "/").casefold()
    return sub.casefold() in p


def _metadata_has_substring(store: FaissStore, sub: str) -> bool:
    s = sub.casefold()
    for m in store.metadata:
        p = str(m.get("path", ""))
        if s in p.casefold():
            return True
    return False


def _metadata_has_any_substring(store: FaissStore, subs: list[str]) -> bool:
    return any(_metadata_has_substring(store, s) for s in subs)


def run_demo_retrieval_benchmark(
    *,
    top_k: int = 12,
    media_filter: str = "both",
) -> DemoRetrievalResult:
    data = _load_spec()
    cases_in = data.get("cases") or []
    if not cases_in:
        raise ValueError("demo_retrieval.json has no cases")

    try:
        clip = get_clip_service()
        store = get_faiss_store()
    except CorruptIndexError:
        raise

    ntotal = len(store.metadata)
    k_scan = min(ntotal, _MAX_RANK_SCAN) if ntotal else 0
    out_cases: list[DemoCaseResult] = []

    for c in cases_in:
        q = str(c.get("query", "")).strip()
        sub = str(c.get("path_includes", "")).strip()
        alt_raw = c.get("path_includes_any")
        alt_subs = [str(s).strip() for s in alt_raw] if isinstance(alt_raw, list) else []
        alt_subs = [s for s in alt_subs if s]
        all_subs = [sub, *alt_subs] if sub else alt_subs
        label = str(c.get("label", "")).strip() or sub
        if not q or not all_subs:
            continue

        in_meta = _metadata_has_any_substring(store, all_subs) if ntotal else False
        note: str | None = None
        if not in_meta:
            note = "No path in the index contains this expected video/image key — run fetch_demo_dataset.py, then index the demo_corpus folder (Replace entire index if needed)."

        t0 = time.perf_counter()
        rank: int | None = None
        best_score: float | None = None
        if not in_meta or not k_scan:
            raw: list = []
            elapsed_ms = (time.perf_counter() - t0) * 1000
        else:
            qvec = clip.encode_text([q])[0]
            # k_scan ≈ ntotal: full ordering so we can report true rank (first matching row in result list).
            raw = _search_with_media_filter(store, qvec, k_scan, media_filter)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            for i, (meta, score) in enumerate(raw):
                path = str(meta.get("path", ""))
                if any(_path_matches_sub(path, s) for s in all_subs):
                    rank = i + 1
                    best_score = float(score)
                    break

        if in_meta and rank is None and k_scan and raw:
            if k_scan < ntotal and media_filter == "both":
                note = (
                    f"Match in metadata but not in the first {k_scan} FAISS hits (index has {ntotal} vectors). "
                    "Increase cap or use a more specific query."
                )
            elif media_filter != "both":
                note = "This path is indexed but excluded by the media filter (e.g. use “both” for the sample MP4 cases)."
        in_top = rank is not None and rank <= top_k

        out_cases.append(
            DemoCaseResult(
                label=label,
                query=q,
                path_includes=sub,
                expected_in_index=in_meta,
                rank=rank,
                in_top_k=in_top,
                best_score=best_score,
                latency_ms=round(elapsed_ms, 2),
                note=note,
            )
        )

    n = len(out_cases)
    if n == 0:
        raise ValueError("No valid cases after parsing spec")

    passed = sum(1 for c in out_cases if c.in_top_k)
    recall = passed / n
    count_in = sum(1 for c in out_cases if c.expected_in_index)
    count_missing = n - count_in

    return DemoRetrievalResult(
        ntotal=ntotal,
        top_k=top_k,
        media_filter=media_filter,
        spec_version=int(data.get("version", 1)),
        spec_description=str(data.get("description", "")).strip(),
        cases=out_cases,
        pass_count=passed,
        case_count=n,
        recall=round(recall, 4),
        search_rank_depth=k_scan,
        count_expected_in_index=count_in,
        count_not_in_index=count_missing,
    )
