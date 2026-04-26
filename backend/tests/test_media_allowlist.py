import os
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("faiss")

from app.services.faiss_store import FaissStore


def test_media_path_is_allowed_for_absolute_indexed_file(tmp_path: Path) -> None:
    media_root = tmp_path / "data"
    media_root.mkdir()
    outside = tmp_path / "Videos"
    clip = outside / "clip.mp4"
    clip.parent.mkdir(parents=True)
    clip.touch()

    st = FaissStore(
        dim=2,
        index_path=tmp_path / "idx.bin",
        sqlite_path=tmp_path / "meta.sqlite",
    )
    st.replace(
        np.zeros((1, 2), dtype=np.float32),
        [{"path": str(clip), "kind": "video", "time_sec": 0.0}],
    )
    logical = os.path.normpath(str(clip))
    assert st.media_path_is_allowed(logical, media_root)


def test_media_path_rejects_unindexed_outside_media_root(tmp_path: Path) -> None:
    media_root = tmp_path / "data"
    media_root.mkdir()
    secret = tmp_path / "secret" / "nope.mp4"
    secret.parent.mkdir(parents=True)
    secret.touch()

    st = FaissStore(
        dim=2,
        index_path=tmp_path / "idx2.bin",
        sqlite_path=tmp_path / "meta2.sqlite",
    )
    st.replace(
        np.zeros((1, 2), dtype=np.float32),
        [{"path": str(media_root / "ok.mp4"), "kind": "video", "time_sec": 0.0}],
    )
    (media_root / "ok.mp4").touch()
    logical = os.path.normpath(str(secret))
    assert not st.media_path_is_allowed(logical, media_root)
