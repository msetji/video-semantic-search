import logging

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.exceptions import CorruptIndexError
from app.schemas.schemas import (
    BenchmarkSearchRequest,
    BenchmarkSearchResponse,
    DemoRetrievalRequest,
    DemoRetrievalResponse,
    DemoRetrievalCaseOut,
)
from app.services.demo_retrieval_benchmark import run_demo_retrieval_benchmark
from app.services.search_benchmark import run_search_benchmark

logger = logging.getLogger(__name__)

router = APIRouter(tags=["benchmarks"])

_EPS = 1e-8

# Subfolder of MEDIA_ROOT used by the fetch_demo_dataset script and demo retrieval spec.
_DEMO_SUBDIR = "demo_corpus"


@router.get("/benchmarks/demo-corpus")
def demo_corpus_info() -> dict:
    """Client uses `index_root_path_for_api` with `replace_entire_index: true` to reindex only the demo set."""
    media = settings.media_root.resolve()
    abs_demo = (media / _DEMO_SUBDIR).resolve()
    return {
        "index_root_path_for_api": _DEMO_SUBDIR,
        "media_root": str(media),
        "demo_corpus_absolute": str(abs_demo),
        "demo_corpus_exists": abs_demo.is_dir(),
    }


@router.post("/benchmarks/search", response_model=BenchmarkSearchResponse)
def benchmark_search(body: BenchmarkSearchRequest) -> BenchmarkSearchResponse:
    """Measure search latency and compare CLIP retrieval strength to random baselines."""
    try:
        r = run_search_benchmark(
            iterations=body.iterations,
            top_k=body.top_k,
            media_filter=body.media_filter,
            seed=body.seed,
        )
    except CorruptIndexError as e:
        logger.error("Benchmark aborted — corrupt index: %s", e)
        raise HTTPException(status_code=503, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:  # noqa: BLE001
        logger.exception("Benchmark failed")
        raise HTTPException(status_code=500, detail=str(e)) from e

    rc = r.random_corpus_mean_topk + _EPS
    gib = r.gibberish_mean_topk + _EPS
    return BenchmarkSearchResponse(
        ntotal=r.ntotal,
        iterations=r.iterations,
        top_k=r.top_k,
        media_filter=r.media_filter,
        latency_mean_s=r.latency_mean_s,
        latency_p50_s=r.latency_p50_s,
        latency_p95_s=r.latency_p95_s,
        qps=r.qps,
        semantic_mean_topk=r.semantic_mean_topk,
        random_corpus_mean_topk=r.random_corpus_mean_topk,
        gibberish_mean_topk=r.gibberish_mean_topk,
        random_query_unit_mean_topk=r.random_query_unit_mean_topk,
        semantic_over_random_corpus=r.semantic_mean_topk / rc,
        semantic_over_gibberish=r.semantic_mean_topk / gib,
    )


@router.post("/benchmarks/demo-retrieval", response_model=DemoRetrievalResponse)
def benchmark_demo_retrieval(body: DemoRetrievalRequest) -> DemoRetrievalResponse:
    """Run labeled queries from `backend/benchmarks/demo_retrieval.json` and report if expected paths land in top-k."""
    try:
        r = run_demo_retrieval_benchmark(
            top_k=body.top_k,
            media_filter=body.media_filter,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except CorruptIndexError as e:
        logger.error("Demo retrieval benchmark aborted — corrupt index: %s", e)
        raise HTTPException(status_code=503, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:  # noqa: BLE001
        logger.exception("Demo retrieval benchmark failed")
        raise HTTPException(status_code=500, detail=str(e)) from e

    return DemoRetrievalResponse(
        ntotal=r.ntotal,
        top_k=r.top_k,
        media_filter=r.media_filter,
        spec_version=r.spec_version,
        spec_description=r.spec_description,
        cases=[
            DemoRetrievalCaseOut(
                label=c.label,
                query=c.query,
                path_includes=c.path_includes,
                expected_in_index=c.expected_in_index,
                rank=c.rank,
                in_top_k=c.in_top_k,
                best_score=c.best_score,
                latency_ms=c.latency_ms,
                note=c.note,
            )
            for c in r.cases
        ],
        pass_count=r.pass_count,
        case_count=r.case_count,
        recall=r.recall,
        search_rank_depth=r.search_rank_depth,
        count_expected_in_index=r.count_expected_in_index,
        count_not_in_index=r.count_not_in_index,
    )
