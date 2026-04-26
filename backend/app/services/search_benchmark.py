"""Search latency + simple retrieval-vs-random baselines for /benchmarks API."""

from __future__ import annotations

import statistics
import time
from dataclasses import dataclass
from typing import Any

import numpy as np

from app.services.clip_service import get_clip_service
from app.services.faiss_store import FaissStore, get_faiss_store

_DEFAULT_QUERIES = (
    "a mountain bike jump in the woods",
    "a person walking on the beach",
    "a dog playing",
    "sunset over water",
    "city skyline at night",
)

_GIBBERISH_QUERIES = (
    "xqmwkfj zzzzz abstract",
    "nonsense symbols qwertyuiop",
)


def _search_with_media_filter(
    store: FaissStore,
    qvec: np.ndarray,
    top_k: int,
    media_filter: str,
) -> list[tuple[dict[str, Any], float]]:
    """Mirror of search API filtering (avoid circular import with api.search)."""
    n = len(store.metadata)
    if n == 0:
        return []
    if media_filter == "both":
        return store.search(qvec, min(top_k, n))
    want_kind = "image" if media_filter == "images" else "video"
    k = min(n, max(top_k * 50, 200))
    while True:
        raw = store.search(qvec, k)
        filtered = [(m, s) for m, s in raw if m.get("kind") == want_kind]
        if len(filtered) >= top_k or k >= n:
            return filtered[:top_k]
        next_k = min(n, max(k * 2, k + top_k * 25))
        if next_k <= k:
            return filtered[:top_k]
        k = next_k


def _mean_topk_scores(results: list[tuple[dict[str, Any], float]]) -> float:
    if not results:
        return 0.0
    return float(statistics.fmean(s for _, s in results))


def _random_corpus_mean_score(
    store: FaissStore,
    qvec: np.ndarray,
    top_k: int,
    rng: np.random.Generator,
) -> float:
    """Mean cosine (IP) between query and `top_k` uniformly random indexed embeddings."""
    n = len(store.metadata)
    if n == 0:
        return 0.0
    k = min(top_k, n)
    ids = rng.choice(n, size=k, replace=False)
    q = np.asarray(qvec, dtype=np.float32).reshape(-1)
    sims: list[float] = []
    for i in ids:
        v = store.reconstruct_vector(int(i))
        sims.append(float(np.dot(q, v)))
    return float(statistics.fmean(sims)) if sims else 0.0


@dataclass(frozen=True)
class SearchBenchmarkResult:
    ntotal: int
    iterations: int
    top_k: int
    media_filter: str
    latency_mean_s: float
    latency_p50_s: float
    latency_p95_s: float
    qps: float
    semantic_mean_topk: float
    random_corpus_mean_topk: float
    gibberish_mean_topk: float
    random_query_unit_mean_topk: float


def run_search_benchmark(
    *,
    iterations: int = 40,
    top_k: int = 10,
    media_filter: str = "both",
    seed: int = 42,
) -> SearchBenchmarkResult:
    clip = get_clip_service()
    store = get_faiss_store()
    if store.is_corrupt:
        raise ValueError("Index is corrupt or missing; run POST /index first.")
    n = len(store.metadata)
    if n == 0:
        raise ValueError("Index is empty; run POST /index first.")

    rng = np.random.default_rng(seed)
    queries = list(_DEFAULT_QUERIES)
    times: list[float] = []
    semantic_means: list[float] = []
    random_corpus_means: list[float] = []
    random_unit_means: list[float] = []

    iters = max(1, iterations)
    for i in range(iters):
        qtext = queries[i % len(queries)]
        t0 = time.perf_counter()
        qv = clip.encode_text([qtext])[0]
        raw = _search_with_media_filter(store, qv, top_k, media_filter)
        times.append(time.perf_counter() - t0)
        semantic_means.append(_mean_topk_scores(raw))
        random_corpus_means.append(_random_corpus_mean_score(store, qv, top_k, rng))

        ru = rng.standard_normal(clip.embedding_dim).astype(np.float32)
        ru /= float(np.linalg.norm(ru)) + 1e-12
        raw_u = _search_with_media_filter(store, ru, top_k, media_filter)
        random_unit_means.append(_mean_topk_scores(raw_u))

    times.sort()
    p50 = statistics.median(times)
    p95 = times[int(0.95 * (len(times) - 1))]
    mean_lat = statistics.fmean(times)

    gib_scores: list[float] = []
    for g in _GIBBERISH_QUERIES:
        gv = clip.encode_text([g])[0]
        raw_g = _search_with_media_filter(store, gv, top_k, media_filter)
        gib_scores.append(_mean_topk_scores(raw_g))
    gib_mean = float(statistics.fmean(gib_scores)) if gib_scores else 0.0

    return SearchBenchmarkResult(
        ntotal=n,
        iterations=iters,
        top_k=top_k,
        media_filter=media_filter,
        latency_mean_s=mean_lat,
        latency_p50_s=p50,
        latency_p95_s=p95,
        qps=(1.0 / mean_lat) if mean_lat > 0 else 0.0,
        semantic_mean_topk=float(statistics.fmean(semantic_means)),
        random_corpus_mean_topk=float(statistics.fmean(random_corpus_means)),
        gibberish_mean_topk=gib_mean,
        random_query_unit_mean_topk=float(statistics.fmean(random_unit_means)),
    )
