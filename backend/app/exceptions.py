class CorruptIndexError(Exception):
    """FAISS vector count and SQLite metadata are out of sync or files are damaged."""
