import { type FormEvent, useMemo, useState } from 'react'
import type { SearchHit, SearchResponse } from './types'
import { MediaPreview } from './components/MediaPreview'
import { absoluteUrlForMediaPreview } from './utils/mediaPaths'
import { About } from './components/About'

//base URL for API calls
const API_BASE = import.meta.env.VITE_API_BASE ?? ''

function App() {

  //track search query, results, loading state, and errors
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchHit[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [indexRootPath, setIndexRootPath] = useState('')
  const [indexStatus, setIndexStatus] = useState<string | null>(null)
  const [page, setPage] = useState<'search' | 'about'>('search')
  const [searchTimingsMs, setSearchTimingsMs] = useState<{
    clip: number
    faiss: number
    total: number
  } | null>(null)


  const mediaBase = useMemo(() => API_BASE.replace(/\/$/, ''), [])

  //sends the query to the backend and updates results
  async function handleSearchFormSubmit(e: FormEvent) {
    e.preventDefault()
    if (!query.trim()) return
    setLoading(true)
    setError(null)
    setSearchTimingsMs(null)
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
      setSearchTimingsMs({
        clip: data.clip_encode_sec * 1000,
        faiss: data.faiss_search_sec * 1000,
        total: data.total_sec * 1000,
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed')
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  //opens a folder picker to make process more streamlined for the user
  async function handleBrowseDirectory() {
    try {
      const res = await fetch(`${API_BASE}/api/system/browse-directory`)
      if (res.ok) {
        const data = await res.json()
        if (data.path) {
          setIndexRootPath(data.path)
        }
      }
    } catch (e) {
      console.error(e)
    }
  }

  //initiates the CLIP embedding and FAISS indexing for selected folder
  async function handleStartIndex() {
    setIndexStatus('Starting index...')
    try {
      const res = await fetch(`${API_BASE}/index`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ root_path: indexRootPath || null, run_in_background: true }),
      })
      if (res.ok) {
        setIndexStatus('Indexing background task started.')
      } else {
        const text = await res.text()
        setIndexStatus('Error: ' + text)
      }
    } catch (e) {
      setIndexStatus('Request failed.')
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
              className="flex w-full max-w-xl flex-col gap-2 sm:flex-row sm:items-center"
            >
              <input
                type="search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder='Try searching using specific keywords'
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
          )}
        </div>
      </header>

      {page === 'search' && (
        <>
          <section className="border-b border-zinc-800 bg-zinc-900/40 px-4 py-3">
            <div className="mx-auto flex max-w-6xl flex-col gap-3 sm:flex-row sm:items-center sm:justify-between text-sm">
              <div className="flex items-center gap-2 w-full max-w-lg">
                <span className="text-zinc-400 font-medium whitespace-nowrap">Indexer:</span>
                <input
                  type="text"
                  value={indexRootPath}
                  onChange={(e) => setIndexRootPath(e.target.value)}
                  placeholder="System directory path"
                  className="flex-1 rounded border border-zinc-700 bg-zinc-950 px-2 py-1.5 text-xs text-white placeholder:text-zinc-600 focus:border-violet-500 focus:outline-none"
                />
                <button
                  onClick={handleBrowseDirectory}
                  className="whitespace-nowrap rounded bg-zinc-800 px-3 py-1.5 text-xs font-medium text-zinc-300 hover:bg-zinc-700 hover:text-white"
                >
                  Choose Directory
                </button>
              </div>
              <div className="flex items-center gap-4">
                {indexStatus && <span className="text-xs text-zinc-400">{indexStatus}</span>}
                <button
                  onClick={handleStartIndex}
                  className="rounded bg-violet-600/20 text-violet-400 px-4 py-1.5 font-medium hover:bg-violet-600/30 whitespace-nowrap"
                >
                  Process Embeddings
                </button>
              </div>
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

            {searchTimingsMs && (
              <p className="mb-4 text-xs text-zinc-500">
                Server timing: CLIP encode {searchTimingsMs.clip.toFixed(1)} ms · FAISS{' '}
                {searchTimingsMs.faiss.toFixed(1)} ms · total {searchTimingsMs.total.toFixed(1)} ms
              </p>
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
                Index a folder to get started, then type anything to search your media.
              </p>
            )}
          </main>
        </>
      )}
      {page === 'about' && <About />}
    </div>
  )
}

export default App
