from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import faiss
import numpy as np

from app.exceptions import CorruptIndexError
from app.services.metadata_store import (
    migrate_json_to_sqlite,
    read_rows,
    row_count,
    write_rows_file,
)

logger = logging.getLogger(__name__)


class FaissStore:
    """Inner-product (cosine) search on L2-normalized CLIP vectors."""

    def __init__(
        self,
        dim: int,
        index_path: Path,
        sqlite_path: Path,
        legacy_json_path: Path | None = None,
    ) -> None:
        self.dim = dim
        self.index_path = index_path
        self.sqlite_path = sqlite_path
        self.legacy_json_path = legacy_json_path
        self._cpu_index: faiss.Index | None = None
        self._gpu_index: faiss.Index | None = None
        self._gpu_res: faiss.StandardGpuResources | None = None
        self.metadata: list[dict[str, Any]] = []
        self.is_corrupt: bool = False

    def load(self) -> bool:
        self.is_corrupt = False
        self._gpu_index = None
        self._gpu_res = None
        if not self.index_path.exists():
            return False
        try:
            cpu = faiss.read_index(str(self.index_path))
        except Exception as e:  # noqa: BLE001
            logger.error("Failed to read FAISS index: %s", e)
            self.is_corrupt = True
            self._cpu_index = None
            self.metadata = []
            return False

        if not self.sqlite_path.exists():
            if self.legacy_json_path and migrate_json_to_sqlite(
                self.legacy_json_path, self.sqlite_path, cpu.ntotal
            ):
                return self.load()
            logger.error("Missing SQLite metadata alongside FAISS index")
            self.is_corrupt = True
            self._cpu_index = None
            self.metadata = []
            return False

        try:
            rows = read_rows(self.sqlite_path)
        except Exception as e:  # noqa: BLE001
            logger.error("Failed to read metadata SQLite: %s", e)
            self.is_corrupt = True
            self._cpu_index = None
            self.metadata = []
            return False

        if cpu.ntotal != len(rows):
            logger.error(
                "Index corrupt: FAISS ntotal=%s != sqlite rows=%s",
                cpu.ntotal,
                len(rows),
            )
            self.is_corrupt = True
            self._cpu_index = None
            self.metadata = []
            return False

        self._cpu_index = cpu
        self.metadata = rows
        return True

    def _ensure_search_index(self) -> faiss.Index:
        if self._cpu_index is None:
            raise RuntimeError("Index not built")
        if self._gpu_index is not None:
            return self._gpu_index
        if faiss.get_num_gpus() > 0:
            self._gpu_res = faiss.StandardGpuResources()
            self._gpu_index = faiss.index_cpu_to_gpu(self._gpu_res, 0, self._cpu_index)
            logger.info("FAISS search using GPU")
            return self._gpu_index
        self._gpu_index = self._cpu_index
        logger.info("FAISS search using CPU")
        return self._gpu_index

    def save(self) -> None:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        cpu = self._cpu_index
        if self._gpu_index is not None and faiss.get_num_gpus() > 0:
            cpu = faiss.index_gpu_to_cpu(self._gpu_index)  # type: ignore[assignment]
        assert cpu is not None
        index_dir = self.index_path.parent
        faiss_new = index_dir / "faiss.index.new"
        sqlite_new = index_dir / "metadata.sqlite.new"
        try:
            faiss.write_index(cpu, str(faiss_new))
            write_rows_file(sqlite_new, self.metadata)
            verify = faiss.read_index(str(faiss_new))
            if verify.ntotal != len(self.metadata):
                raise RuntimeError("FAISS temp ntotal does not match metadata length")
            if row_count(sqlite_new) != len(self.metadata):
                raise RuntimeError("SQLite temp row count does not match metadata")
            os.replace(faiss_new, self.index_path)
            os.replace(sqlite_new, self.sqlite_path)
        except Exception:
            for p in (faiss_new, sqlite_new):
                if p.exists():
                    try:
                        p.unlink()
                    except OSError:
                        pass
            raise

    def replace(self, vectors: np.ndarray, metadata: list[dict[str, Any]]) -> None:
        if vectors.shape[0] != len(metadata):
            raise ValueError("vectors and metadata length mismatch")
        self.is_corrupt = False
        if vectors.size == 0:
            self.metadata = []
            self._cpu_index = faiss.IndexFlatIP(self.dim)
            self._gpu_index = None
            self._gpu_res = None
            return
        if vectors.shape[1] != self.dim:
            raise ValueError("wrong embedding dimension")
        self.metadata = metadata
        self._gpu_index = None
        self._gpu_res = None
        index = faiss.IndexFlatIP(self.dim)
        index.add(vectors.astype(np.float32))
        self._cpu_index = index

    def search(self, query: np.ndarray, top_k: int) -> list[tuple[dict[str, Any], float]]:
        if self.is_corrupt:
            raise CorruptIndexError("Index metadata is inconsistent; run POST /index again")
        if self._cpu_index is None or not self.metadata:
            return []
        query_vector = query.reshape(1, -1).astype(np.float32)
        faiss.normalize_L2(query_vector)
        search_index = self._ensure_search_index()
        max_results = min(top_k, len(self.metadata))
        scores, ids = search_index.search(query_vector, max_results)
        results: list[tuple[dict[str, Any], float]] = []
        for score, i in zip(scores[0], ids[0], strict=True):
            if i < 0:
                continue
            results.append((self.metadata[i], float(score)))
        return results


_store: FaissStore | None = None


def get_faiss_store() -> FaissStore:
    global _store
    if _store is not None:
        return _store
    from app.config import settings
    from app.services.clip_service import get_clip_service

    clip = get_clip_service()
    dim = clip.embedding_dim
    st = FaissStore(
        dim,
        settings.faiss_index_path,
        settings.sqlite_metadata_path,
        legacy_json_path=settings.legacy_metadata_json_path,
    )
    if not st.load():
        if st.is_corrupt:
            _store = st
            return _store
        st.replace(np.zeros((0, dim), dtype=np.float32), [])
    _store = st
    return _store


def reset_faiss_store_singleton() -> None:
    """Clear cached store (e.g. after tests)."""
    global _store
    _store = None
