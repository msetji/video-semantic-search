import { type FormEvent, useEffect, useMemo, useRef, useState } from 'react'
import type { IndexStatus, SearchHit, SearchResponse } from './types'
import { MediaPreview } from './components/MediaPreview'
import { absoluteUrlForMediaPreview } from './utils/mediaPaths'
import { About } from './components/About'
import { Benchmarks } from './components/Benchmarks'
import { Library } from './components/Library'
import { Logs } from './components/Logs'

const API_BASE = import.meta.env.VITE_API_BASE ?? ''

function formatElapsedSeconds(totalSec: number): string {
  if (!Number.isFinite(totalSec) || totalSec < 0) return '0:00'
  const sec = Math.floor(totalSec % 60)
  const min = Math.floor(totalSec / 60) % 60
  const hr = Math.floor(totalSec / 3600)
  if (hr > 0) return `${hr}:${String(min).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
  return `${min}:${String(sec).padStart(2, '0')}`
}

/** Raw CLIP cosine; typical good text–image hits are ~0.22–0.40. */
const MATCH_STRONG_MIN = 0.22
const MATCH_WEAK_MAX = 0.18

function clipMatchLabel(score: number): { text: string; className: string } {
  if (!Number.isFinite(score)) {
    return { text: 'Match', className: 'text-zinc-500' }
  }
  if (score >= MATCH_STRONG_MIN) {
    return { text: 'Strong Match', className: 'text-emerald-400' }
  }
  if (score < MATCH_WEAK_MAX) {
    return { text: 'Weak Match', className: 'text-amber-400/90' }
  }
  return { text: 'Match', className: 'text-zinc-400' }
}

function App() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchHit[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [indexRootPathInput, setIndexRootPathInput] = useState('')
  const [indexRootPaths, setIndexRootPaths] = useState<string[]>([])
  const [replaceEntireIndex, setReplaceEntireIndex] = useState(false)
  const [indexStatus, setIndexStatus] = useState<IndexStatus | null>(null)
  const [cancelling, setCancelling] = useState(false)
  const [topK, setTopK] = useState(12)
  const [mediaFilter, setMediaFilter] = useState<'both' | 'images' | 'videos'>('both')
  const [page, setPage] = useState<'search' | 'library' | 'benchmarks' | 'logs' | 'about'>('search')
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const [, setElapsedTick] = useState(0)

  const mediaBase = useMemo(() => API_BASE.replace(/\/$/, ''), [])

  useEffect(() => {
    if (indexStatus?.status !== 'running') return
    const id = setInterval(() => setElapsedTick((n) => n + 1), 1000)
    return () => clearInterval(id)
  }, [indexStatus?.status])

  async function fetchIndexStatus(): Promise<IndexStatus | null> {
    try {
      const res = await fetch(`${API_BASE}/index/status`)
      if (!res.ok) return null
      return await res.json() as IndexStatus
    } catch {
      return null
    }
  }

  function startPolling() {
    if (pollRef.current) return
    pollRef.current = setInterval(async () => {
      const status = await fetchIndexStatus()
      if (!status) return
      setIndexStatus(status)
      if (status.status !== 'running') {
        clearInterval(pollRef.current!)
        pollRef.current = null
        setCancelling(false)
      }
    }, 1000)
  }

  async function handleCancelIndex() {
    setCancelling(true)
    try {
      await fetch(`${API_BASE}/index/cancel`, { method: 'POST' })
    } catch {
      setCancelling(false)
    }
  }

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [])

  async function handleSearchFormSubmit(e: FormEvent) {
    e.preventDefault()
    if (!query.trim()) return
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: query.trim(),
          top_k: topK,
          media_filter: mediaFilter,
        }),
      })
      if (!res.ok) {
        const text = await res.text()
        throw new Error(text || res.statusText)
      }
      const data: SearchResponse = await res.json()
      setResults(data.results)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed')
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  //opens a folder picker to make process more streamlined for the user
  function addIndexRootPath(path: string) {
    const trimmed = path.trim()
    if (!trimmed) return
    setIndexRootPaths((prev) => (prev.includes(trimmed) ? prev : [...prev, trimmed]))
    setIndexRootPathInput('')
  }

  function removeIndexRootPath(path: string) {
    setIndexRootPaths((prev) => prev.filter((p) => p !== path))
  }

  async function handleBrowseDirectory() {
    try {
      const res = await fetch(`${API_BASE}/api/system/browse-directories`)
      if (res.ok) {
        const data = await res.json()
        if (Array.isArray(data.paths)) {
          setIndexRootPaths((prev) => {
            const merged = new Set(prev)
            for (const raw of data.paths) {
              if (typeof raw === 'string' && raw.trim()) {
                merged.add(raw.trim())
              }
            }
            return Array.from(merged)
          })
        } else if (typeof data.path === 'string' && data.path.trim()) {
          addIndexRootPath(data.path)
        }
      }
    } catch (e) {
      console.error(e)
    }
  }

  async function handleStartIndex() {
    try {
      const res = await fetch(`${API_BASE}/index`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          root_paths: indexRootPaths.length > 0 ? indexRootPaths : null,
          run_in_background: true,
          replace_entire_index: replaceEntireIndex,
        }),
      })
      if (res.ok) {
        const status = await fetchIndexStatus()
        setIndexStatus(status)
        startPolling()
      } else {
        const data = await res.json().catch(() => null)
        setIndexStatus({ status: 'failed', error: data?.detail ?? res.statusText, detail: null, embeddings_written: 0, total_files: 0, files_done: 0, current_file: null, started_at: null, finished_at: null, last_result: null })
      }
    } catch {
      setIndexStatus({ status: 'failed', error: 'Request failed', detail: null, embeddings_written: 0, total_files: 0, files_done: 0, current_file: null, started_at: null, finished_at: null, last_result: null })
    }
  }

  return (
    <div className="min-h-svh bg-zinc-950 text-zinc-100">
      <header className="border-b border-zinc-800 bg-zinc-900/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-6 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-white">
              Semantic Local Media Search
            </h1>
            <p className="mt-1 text-sm text-zinc-400">
              Searching through local photos and videos using natural language.
            </p>
            {/* nav tabs */}
            <div className="flex gap-4 mt-3 text-sm">
              <button
                onClick={() => setPage('search')}
                className={`pb-0.5 border-b-2 transition-colors ${page === 'search' ? 'border-violet-500 text-white' : 'border-transparent text-zinc-500 hover:text-zinc-300'}`}
              >
                Search
              </button>
              <button
                onClick={() => setPage('library')}
                className={`pb-0.5 border-b-2 transition-colors ${page === 'library' ? 'border-violet-500 text-white' : 'border-transparent text-zinc-500 hover:text-zinc-300'}`}
              >
                Library
              </button>
              <button
                onClick={() => setPage('benchmarks')}
                className={`pb-0.5 border-b-2 transition-colors ${page === 'benchmarks' ? 'border-violet-500 text-white' : 'border-transparent text-zinc-500 hover:text-zinc-300'}`}
              >
                Benchmarks
              </button>
              <button
                onClick={() => setPage('logs')}
                className={`pb-0.5 border-b-2 transition-colors ${page === 'logs' ? 'border-violet-500 text-white' : 'border-transparent text-zinc-500 hover:text-zinc-300'}`}
              >
                Logs
              </button>
              <button
                onClick={() => setPage('about')}
                className={`pb-0.5 border-b-2 transition-colors ${page === 'about' ? 'border-violet-500 text-white' : 'border-transparent text-zinc-500 hover:text-zinc-300'}`}
              >
                About
              </button>
            </div>

          </div>
          {page === 'search' && (
            <form
              onSubmit={handleSearchFormSubmit}
              className="flex w-full max-w-3xl flex-col flex-wrap gap-2 sm:flex-row sm:items-center"
            >
              <input
                type="search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder='Try searching using specific keywords'
                className="flex-1 rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-white placeholder:text-zinc-500 focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500"
                aria-label="Search query"
              />
              <select
                value={topK}
                onChange={e => setTopK(Number(e.target.value))}
                className="rounded-lg border border-zinc-700 bg-zinc-950 px-2 py-2 text-sm text-zinc-300 focus:border-violet-500 focus:outline-none"
                aria-label="Number of results"
              >
                {[6, 12, 24, 48].map(n => (
                  <option key={n} value={n}>{n} results</option>
                ))}
              </select>
              <select
                value={mediaFilter}
                onChange={(e) => setMediaFilter(e.target.value as 'both' | 'images' | 'videos')}
                className="rounded-lg border border-zinc-700 bg-zinc-950 px-2 py-2 text-sm text-zinc-300 focus:border-violet-500 focus:outline-none"
                aria-label="Media types to search"
              >
                <option value="both">Images & videos</option>
                <option value="images">Images only</option>
                <option value="videos">Videos only</option>
              </select>
              <button
                type="submit"
                disabled={loading}
                className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white shadow hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? 'Searching…' : 'Search'}
              </button>
            </form>
          )}
        </div>
      </header>

      {page === 'search' && (
        <>
          <section className="border-b border-zinc-800 bg-zinc-900/40 px-4 py-3">
            <div className="mx-auto flex max-w-6xl flex-col gap-3 text-sm">
              {/* directory picker row */}
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-center gap-2 w-full max-w-lg">
                  <span className="text-zinc-400 font-medium whitespace-nowrap">Indexer:</span>
                  <input
                    type="text"
                    value={indexRootPathInput}
                    onChange={(e) => setIndexRootPathInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault()
                        addIndexRootPath(indexRootPathInput)
                      }
                    }}
                    placeholder="Directory path (optional)"
                    className="flex-1 rounded border border-zinc-700 bg-zinc-950 px-2 py-1.5 text-xs text-white placeholder:text-zinc-600 focus:border-violet-500 focus:outline-none"
                  />
                  <button
                    onClick={() => addIndexRootPath(indexRootPathInput)}
                    className="whitespace-nowrap rounded bg-zinc-800 px-3 py-1.5 text-xs font-medium text-zinc-300 hover:bg-zinc-700 hover:text-white"
                  >
                    Add
                  </button>
                  <button
                    onClick={handleBrowseDirectory}
                    className="whitespace-nowrap rounded bg-zinc-800 px-3 py-1.5 text-xs font-medium text-zinc-300 hover:bg-zinc-700 hover:text-white"
                  >
                    Choose Directories
                  </button>
                </div>
                <div className="flex flex-col items-end gap-2 sm:flex-row sm:items-center">
                  <label className="flex cursor-pointer items-center gap-2 text-xs text-zinc-400">
                    <input
                      type="checkbox"
                      checked={replaceEntireIndex}
                      onChange={(e) => setReplaceEntireIndex(e.target.checked)}
                      className="rounded border-zinc-600 bg-zinc-950 text-violet-500 focus:ring-violet-500"
                    />
                    Replace entire index
                  </label>
                  <button
                    onClick={handleStartIndex}
                    disabled={indexStatus?.status === 'running'}
                    className="rounded bg-violet-600/20 text-violet-400 px-4 py-1.5 font-medium hover:bg-violet-600/30 whitespace-nowrap disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {indexStatus?.status === 'running' ? 'Indexing…' : 'Process Embeddings'}
                  </button>
                  {indexStatus?.status === 'running' && (
                    <button
                      onClick={handleCancelIndex}
                      disabled={cancelling}
                      className="rounded border border-zinc-600 px-3 py-1.5 text-xs font-medium text-zinc-400 hover:border-red-600 hover:text-red-400 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {cancelling ? 'Cancelling…' : 'Cancel'}
                    </button>
                  )}
                </div>
              </div>
              {indexRootPaths.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {indexRootPaths.map((path) => (
                    <button
                      key={path}
                      onClick={() => removeIndexRootPath(path)}
                      className="rounded border border-zinc-700 bg-zinc-900 px-2 py-1 text-[11px] text-zinc-300 hover:border-zinc-500 hover:text-white"
                      title="Click to remove"
                    >
                      {path} <span className="text-zinc-500">×</span>
                    </button>
                  ))}
                </div>
              )}

              {/* progress panel */}
              {indexStatus && indexStatus.status !== 'idle' && (
                <div className="rounded-lg border border-zinc-700 bg-zinc-950 px-4 py-3 space-y-2">
                  {/* status line */}
                  <div className="flex items-center justify-between text-xs">
                    <span className={
                      indexStatus.status === 'running' ? 'text-violet-400 font-medium' :
                      indexStatus.status === 'completed' ? 'text-emerald-400 font-medium' :
                      indexStatus.status === 'failed' ? 'text-red-400 font-medium' :
                      indexStatus.status === 'cancelled' ? 'text-zinc-400 font-medium' :
                      'text-zinc-400'
                    }>
                      {indexStatus.status === 'running' && (cancelling ? 'Cancelling…' : 'Indexing…')}
                      {indexStatus.status === 'completed' && 'Done'}
                      {indexStatus.status === 'failed' && 'Failed'}
                      {indexStatus.status === 'cancelled' && 'Cancelled'}
                    </span>
                    <span className="text-zinc-500 tabular-nums">
                      {indexStatus.started_at != null && (
                        <>
                          <span className="text-zinc-400">
                            {indexStatus.status === 'running'
                              ? `Elapsed ${formatElapsedSeconds(Date.now() / 1000 - indexStatus.started_at)}`
                              : indexStatus.finished_at != null
                                ? `Time ${formatElapsedSeconds(indexStatus.finished_at - indexStatus.started_at)}`
                                : null}
                          </span>
                          {(indexStatus.total_files > 0 || indexStatus.status === 'running' || indexStatus.embeddings_written > 0) && ' · '}
                        </>
                      )}
                      {indexStatus.total_files > 0
                        ? `${indexStatus.files_done} / ${indexStatus.total_files} files`
                        : indexStatus.status === 'running' ? 'Scanning…' : ''}
                      {indexStatus.embeddings_written > 0 && ` · ${indexStatus.embeddings_written.toLocaleString()} embeddings`}
                    </span>
                  </div>

                  {/* progress bar */}
                  {indexStatus.total_files > 0 && (
                    <div className="h-1.5 w-full rounded-full bg-zinc-800 overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-300 ${indexStatus.status === 'completed' ? 'bg-emerald-500' : indexStatus.status === 'failed' ? 'bg-red-500' : indexStatus.status === 'cancelled' ? 'bg-zinc-600' : 'bg-violet-500'}`}
                        style={{ width: `${indexStatus.status === 'completed' ? 100 : Math.round((indexStatus.files_done / indexStatus.total_files) * 100)}%` }}
                      />
                    </div>
                  )}

                  {/* current file */}
                  {indexStatus.current_file && indexStatus.status === 'running' && (
                    <p className="truncate text-xs text-zinc-500">
                      Processing: <span className="text-zinc-300">{indexStatus.current_file}</span>
                    </p>
                  )}

                  {/* completed summary */}
                  {indexStatus.status === 'completed' && indexStatus.last_result && (
                    <p className="text-xs text-zinc-500">
                      {indexStatus.last_result.images_indexed} images · {indexStatus.last_result.videos_indexed} videos · {indexStatus.last_result.embeddings.toLocaleString()} total embeddings
                    </p>
                  )}

                  {/* error */}
                  {indexStatus.status === 'failed' && indexStatus.error && (
                    <p className="text-xs text-red-400">{indexStatus.error}</p>
                  )}
                </div>
              )}
            </div>
          </section>

          <main className="mx-auto max-w-6xl px-4 py-8">
            {error && (
              <div
                className="mb-6 rounded-lg border border-red-900/80 bg-red-950/50 px-4 py-3 text-sm text-red-200"
                role="alert"
              >
                {error}
              </div>
            )}

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {results.map((hit) => {
                const src = absoluteUrlForMediaPreview(mediaBase, hit.media_url)
                const match = clipMatchLabel(hit.score)
                return (
                  <article
                    key={`${hit.path}-${hit.time_sec ?? 'img'}-${hit.score}`}
                    className="overflow-hidden rounded-xl border border-zinc-800 bg-zinc-900/60 shadow-sm"
                  >
                    <div className="aspect-video w-full bg-zinc-900">
                      <MediaPreview hit={hit} src={src} />
                    </div>
                    <div className="space-y-1 px-3 py-3">
                      <p className="truncate text-xs text-zinc-500" title={hit.path}>
                        {hit.path}
                      </p>
                      <div className="flex items-center justify-between text-xs text-zinc-400">
                        <span className="rounded bg-zinc-800 px-2 py-0.5 capitalize">
                          {hit.kind}
                        </span>
                        <div
                          className="flex flex-wrap items-baseline justify-end gap-x-1.5 gap-y-0.5 text-right"
                          title={
                            'Score is CLIP cosine similarity × 100. ' +
                            `Strong ≥${(MATCH_STRONG_MIN * 100).toFixed(0)}%, weak <${(MATCH_WEAK_MAX * 100).toFixed(0)}% (cosine). Raw: ${hit.score.toFixed(3)}. ` +
                            'High rankings can still feel accurate even in the 20–40% range.'
                          }
                        >
                          <span className="tabular-nums text-zinc-200">
                            {(hit.score * 100).toFixed(1)}%
                          </span>
                          <span className={`text-[11px] font-medium ${match.className}`}>
                            {match.text}
                          </span>
                        </div>
                      </div>
                    </div>
                  </article>
                )
              })}
            </div>

            {!loading && results.length === 0 && !error && (
              <p className="text-center text-sm text-zinc-500">
                Index a folder to get started, then type anything to search your media.
              </p>
            )}
          </main>
        </>
      )}
      {page === 'library' && <Library />}
      {page === 'benchmarks' && <Benchmarks />}
      {page === 'logs' && <Logs />}
      {page === 'about' && <About />}
    </div>
  )
}

export default App
