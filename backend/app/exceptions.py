class CorruptIndexError(Exception):
    """FAISS vector count and SQLite metadata are out of sync or files are damaged."""


class IndexCancelledError(Exception):
    """Raised inside the indexer when a cancellation has been requested."""
