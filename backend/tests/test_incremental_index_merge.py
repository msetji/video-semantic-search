"""Merge-indexing helpers and FaissStore path removal (optional faiss)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from app.services.media_paths import (
    index_merge_removal_spec,
    metadata_path_key_for_removal_matching,
)


def test_merge_spec_subfolder_under_media_root(tmp_path: Path) -> None:
    media = tmp_path / "data"
    media.mkdir()
    scan = media / "vacation" / "2024"
    scan.mkdir(parents=True)
    spec = index_merge_removal_spec(scan, media)
    assert not spec.file_paths
    assert spec.directory_prefix_keys == frozenset(
        {metadata_path_key_for_removal_matching("vacation/2024")}
    )
    assert spec.remove_all_non_absolute_paths is False


def test_merge_spec_whole_media_root(tmp_path: Path) -> None:
    media = tmp_path / "data"
    media.mkdir()
    spec = index_merge_removal_spec(media, media)
    assert spec.remove_all_non_absolute_paths is True
    assert not spec.directory_prefix_keys


def test_merge_spec_outside_media_root(tmp_path: Path) -> None:
    media = tmp_path / "data"
    media.mkdir()
    outside = tmp_path / "Videos" / "Proj"
    outside.mkdir(parents=True)
    spec = index_merge_removal_spec(outside, media)
    assert not spec.file_paths
    assert spec.remove_all_non_absolute_paths is False
    expected = metadata_path_key_for_removal_matching(str(outside.resolve()))
    assert spec.directory_prefix_keys == frozenset({expected})


def test_metadata_path_key_unifies_separators() -> None:
    a = metadata_path_key_for_removal_matching(r"a\b\c.mp4")
    b = metadata_path_key_for_removal_matching("a/b/c.mp4")
    assert a == b


def test_remove_paths_matches_mixed_separators() -> None:
    pytest.importorskip("faiss")
    from app.services.faiss_store import FaissStore

    dim = 3
    st = FaissStore(dim=dim, index_path=Path("/nonexistent/a.bin"), sqlite_path=Path("/nonexistent/b.sqlite"))
    meta = [
        {"path": r"vacation\a.jpg", "kind": "image", "time_sec": None},
        {"path": "other/b.jpg", "kind": "image", "time_sec": None},
    ]
    vecs = np.eye(3, dim, dtype=np.float32)
    st.replace(vecs, meta)
    prefix = metadata_path_key_for_removal_matching("vacation")
    removed = st.remove_paths(set(), {prefix})
    assert removed == 1
    assert len(st.metadata) == 1
    assert "other" in st.metadata[0]["path"]
