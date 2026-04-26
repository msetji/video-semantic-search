import { useCallback, useEffect, useState } from 'react'
import type { LibraryDirectory, LibraryFile, LibraryResponse } from '../types'

const API_BASE = import.meta.env.VITE_API_BASE ?? ''

function formatDuration(sec: number | null): string {
  if (sec === null) return ''
  const m = Math.floor(sec / 60)
  const s = Math.floor(sec % 60)
  return m > 0 ? `${m}m ${s}s` : `${s}s`
}

function FileRow({
  file,
  onDelete,
  deleting,
}: {
  file: LibraryFile
  onDelete: (path: string) => void
  deleting: boolean
}) {
  return (
    <div className="flex items-center gap-3 px-4 py-2 text-xs text-zinc-400 hover:bg-zinc-800/40 group">
      <span className="w-3 shrink-0" />
      <span
        className={`shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium ${
          file.kind === 'video' ? 'bg-blue-900/50 text-blue-300' : 'bg-zinc-700 text-zinc-300'
        }`}
      >
        {file.kind}
      </span>
      <span className="flex-1 truncate text-zinc-300" title={file.path}>
        {file.name}
      </span>
      <span className="shrink-0 text-zinc-600">
        {file.kind === 'video'
          ? `${file.frame_count} frames · ${formatDuration(file.duration_sec)}`
          : '1 embedding'}
      </span>
      <button
        onClick={() => onDelete(file.path)}
        disabled={deleting}
        className="shrink-0 rounded px-2 py-0.5 text-[10px] text-red-500 opacity-0 group-hover:opacity-100 hover:bg-red-950/60 disabled:opacity-30 transition-opacity"
        title="Remove embeddings for this file"
      >
        Remove
      </button>
    </div>
  )
}

function DirectoryRow({
  dir,
  onDeleteFile,
  onDeleteDirectory,
  deletingPaths,
}: {
  dir: LibraryDirectory
  onDeleteFile: (path: string) => void
  onDeleteDirectory: (path: string) => void
  deletingPaths: Set<string>
}) {
  const [expanded, setExpanded] = useState(false)
  const isDeleting = deletingPaths.has(dir.path)

  return (
    <div className="border border-zinc-800 rounded-lg overflow-hidden">
      {/* directory header */}
      <div
        className="flex items-center gap-3 px-4 py-3 bg-zinc-900 cursor-pointer select-none hover:bg-zinc-800/60 group"
        onClick={() => setExpanded((v) => !v)}
      >
        <span className="shrink-0 text-zinc-500 text-xs transition-transform" style={{ transform: expanded ? 'rotate(90deg)' : undefined }}>
          ▶
        </span>
        <span className="flex-1 truncate text-sm font-medium text-zinc-200" title={dir.path}>
          {dir.name}
        </span>
        <span className="shrink-0 text-xs text-zinc-500">
          {dir.file_count} {dir.file_count === 1 ? 'file' : 'files'} · {dir.embedding_count.toLocaleString()} embeddings
        </span>
        <button
          onClick={(e) => {
            e.stopPropagation()
            onDeleteDirectory(dir.path)
          }}
          disabled={isDeleting}
          className="shrink-0 rounded px-2 py-1 text-xs text-red-500 opacity-0 group-hover:opacity-100 hover:bg-red-950/60 disabled:opacity-30 transition-opacity ml-2"
          title="Remove all embeddings in this directory"
        >
          Remove all
        </button>
      </div>

      {/* file list */}
      {expanded && (
        <div className="divide-y divide-zinc-800/60">
          {dir.files.map((file) => (
            <FileRow
              key={file.path}
              file={file}
              onDelete={onDeleteFile}
              deleting={deletingPaths.has(file.path)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export function Library() {
  const [library, setLibrary] = useState<LibraryResponse | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [deletingPaths, setDeletingPaths] = useState<Set<string>>(new Set())
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const fetchLibrary = useCallback(async () => {
    setLoadError(null)
    try {
      const res = await fetch(`${API_BASE}/library`)
      if (!res.ok) {
        const data = await res.json().catch(() => null)
        setLoadError(data?.detail ?? res.statusText)
        return
      }
      setLibrary(await res.json())
    } catch {
      setLoadError('Could not reach the backend.')
    }
  }, [])

  useEffect(() => { fetchLibrary() }, [fetchLibrary])

  async function removeEntries(paths: string[], directories: string[]) {
    const allKeys = [...paths, ...directories]
    setDeletingPaths((prev) => new Set([...prev, ...allKeys]))
    setDeleteError(null)
    try {
      const res = await fetch(`${API_BASE}/library/remove`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ paths, directories }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => null)
        setDeleteError(data?.detail ?? res.statusText)
      } else {
        await fetchLibrary()
      }
    } catch {
      setDeleteError('Delete request failed.')
    } finally {
      setDeletingPaths((prev) => {
        const next = new Set(prev)
        allKeys.forEach((k) => next.delete(k))
        return next
      })
    }
  }

  function handleDeleteFile(path: string) {
    if (!confirm(`Remove embeddings for:\n${path}?`)) return
    removeEntries([path], [])
  }

  function handleDeleteDirectory(path: string) {
    if (!confirm(`Remove all embeddings under:\n${path}?\n\nThis cannot be undone without re-indexing.`)) return
    removeEntries([], [path])
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 space-y-6">
      {/* header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-white">Embedded Library</h2>
          {library && (
            <p className="text-sm text-zinc-500 mt-0.5">
              {library.total_files} {library.total_files === 1 ? 'file' : 'files'} · {library.total_embeddings.toLocaleString()} total embeddings across {library.directories.length} {library.directories.length === 1 ? 'directory' : 'directories'}
            </p>
          )}
        </div>
        <button
          onClick={fetchLibrary}
          className="text-xs text-zinc-500 hover:text-zinc-300 px-3 py-1.5 rounded border border-zinc-700 hover:border-zinc-600"
        >
          Refresh
        </button>
      </div>

      {loadError && (
        <div className="rounded-lg border border-red-900/80 bg-red-950/40 px-4 py-3 text-sm text-red-300">
          {loadError}
        </div>
      )}

      {deleteError && (
        <div className="rounded-lg border border-red-900/80 bg-red-950/40 px-4 py-3 text-sm text-red-300">
          {deleteError}
        </div>
      )}

      {library && library.directories.length === 0 && (
        <p className="text-center text-sm text-zinc-500 py-12">
          No embeddings yet. Index a folder on the Search tab to get started.
        </p>
      )}

      {library && library.directories.length > 0 && (
        <div className="space-y-3">
          {library.directories.map((dir) => (
            <DirectoryRow
              key={dir.path}
              dir={dir}
              onDeleteFile={handleDeleteFile}
              onDeleteDirectory={handleDeleteDirectory}
              deletingPaths={deletingPaths}
            />
          ))}
        </div>
      )}

      {!library && !loadError && (
        <p className="text-center text-sm text-zinc-500 py-12">Loading…</p>
      )}
    </div>
  )
}
