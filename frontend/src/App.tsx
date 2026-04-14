import { type FormEvent, useMemo, useState } from 'react'

import {
  absoluteUrlForMediaPreview,
  isRasterImageFilePath,
  previewUsesVideoElement,
} from './mediaPaths'

const API_BASE = import.meta.env.VITE_API_BASE ?? ''

type SearchHit = {
  path: string
  kind: string
  time_sec: number | null
  score: number
  media_url: string
}

type SearchResponse = {
  query: string
  results: SearchHit[]
}

function MediaPreview({
  hit,
  src,
}: {
  hit: SearchHit
  src: string
}) {
  if (previewUsesVideoElement(hit)) {
    return (
      <video
        className="h-full w-full object-cover"
        src={src}
        muted
        playsInline
        preload="metadata"
        onLoadedMetadata={(e) => {
          const el = e.currentTarget
          const t = hit.time_sec ?? 0
          el.currentTime = Math.min(Math.max(0, t), Math.max(0, el.duration - 0.05))
        }}
      />
    )
  }
  if (isRasterImageFilePath(hit.path)) {
    return (
      <img src={src} alt="" className="h-full w-full object-cover" loading="lazy" />
    )
  }
  return (
    <div className="flex h-full w-full items-center justify-center bg-zinc-900 text-sm text-zinc-500">
      Unsupported preview
    </div>
  )
}

function App() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchHit[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const mediaBase = useMemo(() => API_BASE.replace(/\/$/, ''), [])

  async function handleSearchFormSubmit(e: FormEvent) {
    e.preventDefault()
    if (!query.trim()) return
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query.trim(), top_k: 12 }),
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

  return (
    <div className="min-h-svh bg-zinc-950 text-zinc-100">
      <header className="border-b border-zinc-800 bg-zinc-900/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-6 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-white">
              Semantic media search
            </h1>
            <p className="mt-1 text-sm text-zinc-400">
              Natural language over locally indexed photos & video frames (CLIP +
              FAISS).
            </p>
          </div>
          <form
            onSubmit={handleSearchFormSubmit}
            className="flex w-full max-w-xl flex-col gap-2 sm:flex-row sm:items-center"
          >
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder='Try "a mountain bike jump in the woods"'
              className="flex-1 rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-white placeholder:text-zinc-500 focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500"
              aria-label="Search query"
            />
            <button
              type="submit"
              disabled={loading}
              className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white shadow hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? 'Searching…' : 'Search'}
            </button>
          </form>
        </div>
      </header>

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
                    <span>score {(hit.score * 100).toFixed(1)}%</span>
                  </div>
                </div>
              </article>
            )
          })}
        </div>

        {!loading && results.length === 0 && !error && (
          <p className="text-center text-sm text-zinc-500">
            Run the API indexer, then search — or try a query above.
          </p>
        )}
      </main>
    </div>
  )
}

export default App
