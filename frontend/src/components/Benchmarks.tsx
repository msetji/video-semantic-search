import { useEffect, useRef, useState } from 'react'
import type { BenchmarkSearchResponse, DemoCorpusInfo, DemoRetrievalResponse, IndexStatus } from '../types'

const API_BASE = import.meta.env.VITE_API_BASE ?? ''

const INDEX_POLL_MS = 1000
const INDEX_TIMEOUT_MS = 30 * 60 * 1000

function formatMs(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return '—'
  return `${(seconds * 1000).toFixed(2)} ms`
}

export function Benchmarks() {
  const [iterations, setIterations] = useState(40)
  const [topK, setTopK] = useState(10)
  const [mediaFilter, setMediaFilter] = useState<'both' | 'images' | 'videos'>('both')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<BenchmarkSearchResponse | null>(null)

  const [demoTopK, setDemoTopK] = useState(12)
  const [demoMedia, setDemoMedia] = useState<'both' | 'images' | 'videos'>('both')
  const [demoLoading, setDemoLoading] = useState(false)
  const [demoError, setDemoError] = useState<string | null>(null)
  const [demoResult, setDemoResult] = useState<DemoRetrievalResponse | null>(null)
  const [demoCorpusInfo, setDemoCorpusInfo] = useState<DemoCorpusInfo | null>(null)
  const [showDemoReplaceModal, setShowDemoReplaceModal] = useState(false)
  const [demoIndexStatus, setDemoIndexStatus] = useState<IndexStatus | null>(null)
  const [demoPhase, setDemoPhase] = useState<'idle' | 'indexing' | 'testing'>('idle')
  const indexPollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    return () => {
      if (indexPollRef.current) {
        clearInterval(indexPollRef.current)
        indexPollRef.current = null
      }
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const res = await fetch(`${API_BASE}/benchmarks/demo-corpus`)
        if (!res.ok) return
        const j = await res.json() as DemoCorpusInfo
        if (!cancelled) setDemoCorpusInfo(j)
      } catch {
        /* optional */
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  async function fetchIndexStatus(): Promise<IndexStatus | null> {
    try {
      const res = await fetch(`${API_BASE}/index/status`)
      if (!res.ok) return null
      return await res.json() as IndexStatus
    } catch {
      return null
    }
  }

  function stopIndexPoll() {
    if (indexPollRef.current) {
      clearInterval(indexPollRef.current)
      indexPollRef.current = null
    }
  }

  async function waitForIndexJob(): Promise<void> {
    const time0 = Date.now()
    const jobStartedSec = time0 / 1000
    let sawRunning = false
    return new Promise((resolve, reject) => {
      stopIndexPoll()
      const tick = async () => {
        if (Date.now() - time0 > INDEX_TIMEOUT_MS) {
          stopIndexPoll()
          reject(new Error('Indexing timed out after 30 minutes.'))
          return
        }
        const s = await fetchIndexStatus()
        if (!s) return
        setDemoIndexStatus(s)
        if (s.status === 'running') sawRunning = true
        if (s.status === 'failed' || s.status === 'cancelled') {
          stopIndexPoll()
          reject(new Error(s.error || `Indexing ${s.status}`))
          return
        }
        if (s.status === 'completed') {
          const fin = s.finished_at
          const finishedThisJob =
            fin != null && fin >= jobStartedSec - 1
          if (sawRunning || finishedThisJob) {
            stopIndexPoll()
            resolve()
          }
        }
      }
      void tick()
      indexPollRef.current = setInterval(() => void tick(), INDEX_POLL_MS)
    })
  }

  async function runReplaceIndexAndDemoTest() {
    setShowDemoReplaceModal(false)
    setDemoLoading(true)
    setDemoError(null)
    setDemoResult(null)
    setDemoIndexStatus(null)
    setDemoPhase('indexing')
    try {
      const infoRes = await fetch(`${API_BASE}/benchmarks/demo-corpus`)
      if (!infoRes.ok) {
        throw new Error('Could not read demo corpus path from the server.')
      }
      const info = await infoRes.json() as DemoCorpusInfo
      if (!info.demo_corpus_exists) {
        throw new Error(
          'The demo_corpus folder is missing under your media root. From the repository root run: python scripts/fetch_demo_dataset.py',
        )
      }
      const idx = await fetch(`${API_BASE}/index`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          root_path: info.index_root_path_for_api,
          run_in_background: true,
          replace_entire_index: true,
        }),
      })
      if (idx.status === 409) {
        throw new Error(
          'Another indexing job is already running. Wait for it to finish, or use Cancel on the Search tab, then try again.',
        )
      }
      if (idx.status !== 202) {
        const text = await idx.text()
        let detail = text || 'Index request failed'
        try {
          const j = JSON.parse(text) as { detail?: string }
          if (typeof j.detail === 'string') detail = j.detail
        } catch {
          /* keep */
        }
        throw new Error(detail)
      }
      await waitForIndexJob()
      setDemoPhase('testing')
      const res = await fetch(`${API_BASE}/benchmarks/demo-retrieval`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          top_k: demoTopK,
          media_filter: demoMedia,
        }),
      })
      if (!res.ok) {
        const text = await res.text()
        let detail = text || res.statusText
        try {
          const j = JSON.parse(text) as { detail?: string }
          if (typeof j.detail === 'string') detail = j.detail
        } catch {
          /* keep */
        }
        throw new Error(detail)
      }
      setDemoResult(await res.json() as DemoRetrievalResponse)
    } catch (e) {
      setDemoError(e instanceof Error ? e.message : 'Demo test failed')
      setDemoResult(null)
    } finally {
      setDemoLoading(false)
      setDemoPhase('idle')
      setDemoIndexStatus(null)
      stopIndexPoll()
    }
  }

  async function runBenchmark() {
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const res = await fetch(`${API_BASE}/benchmarks/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          iterations,
          top_k: topK,
          media_filter: mediaFilter,
        }),
      })
      if (!res.ok) {
        const text = await res.text()
        let detail = text || res.statusText
        try {
          const j = JSON.parse(text) as { detail?: string }
          if (typeof j.detail === 'string') detail = j.detail
        } catch {
          /* keep text */
        }
        throw new Error(detail)
      }
      setResult(await res.json() as BenchmarkSearchResponse)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Benchmark failed')
    } finally {
      setLoading(false)
    }
  }

  async function runDemoRetrieval() {
    setDemoLoading(true)
    setDemoError(null)
    setDemoResult(null)
    try {
      const res = await fetch(`${API_BASE}/benchmarks/demo-retrieval`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          top_k: demoTopK,
          media_filter: demoMedia,
        }),
      })
      if (!res.ok) {
        const text = await res.text()
        let detail = text || res.statusText
        try {
          const j = JSON.parse(text) as { detail?: string }
          if (typeof j.detail === 'string') detail = j.detail
        } catch {
          /* keep */
        }
        throw new Error(detail)
      }
      setDemoResult(await res.json() as DemoRetrievalResponse)
    } catch (e) {
      setDemoError(e instanceof Error ? e.message : 'Demo retrieval test failed')
    } finally {
      setDemoLoading(false)
    }
  }

  return (
    <main className="mx-auto max-w-4xl px-4 py-10 space-y-8 text-zinc-300">
      <section>
        <h2 className="text-2xl font-semibold text-white mb-2">Search benchmarks</h2>
        <p className="text-sm text-zinc-400 leading-relaxed max-w-2xl">
          {`Runs the same CLIP + FAISS path as live search on a rotating set of canned queries, reports latency (mean / p50 / p95), and compares mean top-${topK} cosine similarity against baselines: random embeddings from your index, nonsense text, and a random unit query vector.`}
        </p>
      </section>

      <section>
        <h3 className="text-lg font-medium text-white mb-2">Demo corpus retrieval (precision @k)</h3>
        <p className="text-sm text-zinc-400 leading-relaxed max-w-2xl mb-3">
          The benchmark table checks
          {' '}
          <span className="text-zinc-300">(query → path substring)</span>
          {' '}
          pairs. Use
          {' '}
          <span className="text-zinc-300">media: both</span>
          {' '}
          for the sample MP4s. The table shows true rank (deep search) and whether each expected file lands in your Top-K.
        </p>
        <div
          className="mb-4 rounded-lg border border-rose-900/50 bg-rose-950/30 px-4 py-3 text-sm text-rose-100/95 leading-relaxed"
          role="note"
        >
          <p className="font-medium text-rose-200">Replacing the index deletes existing embeddings</p>
          <p className="mt-1.5 text-rose-100/80">
            <span className="text-amber-200/90 font-medium">Replace index &amp; run demo</span>
            {' '}
            will wipe the current FAISS + SQLite index, embed only
            {' '}
            <code className="rounded bg-zinc-900/80 px-1 py-0.5 text-xs">data/demo_corpus</code>
            (relative to the server media root), then run the retrieval test. You must have downloaded files first
            (
            <code className="text-xs">python scripts/fetch_demo_dataset.py</code>
            from the repo root
            {demoCorpusInfo && !demoCorpusInfo.demo_corpus_exists && (
              <span className="text-rose-200"> — on this machine the folder is still missing; run the script before indexing.</span>
            )}
            ).
            {' '}
            To score the demo without touching your current index, use
            {' '}
            <span className="text-amber-200/90">Run test (current index)</span>
            .
          </p>
        </div>
        <div className="flex flex-col gap-4 sm:flex-row sm:flex-wrap sm:items-end rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
          <label className="flex flex-col gap-1 text-xs text-zinc-400">
            Top-K
            <select
              value={demoTopK}
              onChange={(e) => setDemoTopK(Number(e.target.value))}
              disabled={demoLoading}
              className="rounded-lg border border-zinc-700 bg-zinc-950 px-2 py-2 text-sm text-zinc-200 w-32 disabled:opacity-50"
            >
              {[5, 8, 10, 12, 20, 24, 48].map((k) => (
                <option key={k} value={k}>{k}</option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-xs text-zinc-400">
            Media filter
            <select
              value={demoMedia}
              onChange={(e) => setDemoMedia(e.target.value as typeof demoMedia)}
              disabled={demoLoading}
              className="rounded-lg border border-zinc-700 bg-zinc-950 px-2 py-2 text-sm text-zinc-200 w-40 disabled:opacity-50"
            >
              <option value="both">Images & videos</option>
              <option value="images">Images only</option>
              <option value="videos">Videos only</option>
            </select>
          </label>
          <div className="flex flex-col gap-2 w-full sm:w-auto sm:ml-auto sm:items-end">
            <div className="flex flex-col sm:flex-row gap-2 w-full sm:w-auto">
              <button
                type="button"
                onClick={() => setShowDemoReplaceModal(true)}
                disabled={demoLoading}
                className="rounded-lg border border-amber-600/60 bg-amber-950/50 px-4 py-2.5 text-sm font-medium text-amber-100 hover:bg-amber-950/70 disabled:opacity-50 disabled:cursor-not-allowed w-full sm:w-auto"
              >
                {demoPhase === 'indexing' ? 'Indexing…' : demoPhase === 'testing' ? 'Testing…' : 'Replace index & run demo'}
              </button>
              <button
                type="button"
                onClick={runDemoRetrieval}
                disabled={demoLoading}
                className="rounded-lg border border-zinc-600 bg-zinc-800/50 px-4 py-2.5 text-sm font-medium text-zinc-200 hover:bg-zinc-800 disabled:opacity-50 disabled:cursor-not-allowed w-full sm:w-auto"
              >
                {demoLoading ? (demoPhase === 'idle' ? 'Running…' : 'Busy…') : 'Run test (current index)'}
              </button>
            </div>
            {demoCorpusInfo && (
              <p className="text-[11px] text-zinc-500 max-w-sm text-right" title={demoCorpusInfo.demo_corpus_absolute}>
                Server:
                {' '}
                {demoCorpusInfo.demo_corpus_exists ? 'demo_corpus on disk' : 'demo_corpus missing'}
              </p>
            )}
          </div>
        </div>
        {showDemoReplaceModal && (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70"
            role="dialog"
            aria-modal="true"
            aria-labelledby="demo-replace-title"
            onClick={() => !demoLoading && setShowDemoReplaceModal(false)}
          >
            <div
              className="w-full max-w-md rounded-xl border border-zinc-600 bg-zinc-900 p-5 shadow-xl"
              onClick={(e) => e.stopPropagation()}
            >
              <h4 id="demo-replace-title" className="text-lg font-semibold text-white">Replace the entire index?</h4>
              <p className="mt-3 text-sm text-zinc-300 leading-relaxed">
                This will
                {' '}
                <span className="text-amber-200/95 font-medium">permanently remove all current embeddings</span>
                {' '}
                on the server, then reindex
                only
                {' '}
                <code className="rounded bg-zinc-950 px-1.5 py-0.5 text-amber-100/90 text-xs">data/demo_corpus</code>
                . Personal photos or other folders you indexed earlier will
                need to be reindexed from the Search tab.
              </p>
              {demoCorpusInfo && !demoCorpusInfo.demo_corpus_exists && (
                <p className="mt-3 text-sm text-rose-300">
                  The demo folder does not exist yet. Run
                  {' '}
                  <code className="text-xs">python scripts/fetch_demo_dataset.py</code>
                  {' '}
                  from the repository root, then return here.
                </p>
              )}
              <div className="mt-5 flex flex-col-reverse sm:flex-row gap-2 sm:justify-end">
                <button
                  type="button"
                  onClick={() => setShowDemoReplaceModal(false)}
                  className="rounded-lg border border-zinc-600 px-4 py-2 text-sm text-zinc-300 hover:bg-zinc-800"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={runReplaceIndexAndDemoTest}
                  disabled={demoCorpusInfo != null && !demoCorpusInfo.demo_corpus_exists}
                  className="rounded-lg bg-amber-700/90 px-4 py-2 text-sm font-medium text-white hover:bg-amber-600 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Replace index and run
                </button>
              </div>
            </div>
          </div>
        )}
        {demoPhase === 'indexing' && (
          <div className="mt-3 rounded-lg border border-zinc-700 bg-zinc-950/80 px-4 py-2 text-xs text-zinc-400">
            <p className="text-violet-300/90">
              Indexing demo corpus…
              {demoIndexStatus?.status === 'running' && demoIndexStatus.total_files > 0
                ? ` ${demoIndexStatus.files_done} / ${demoIndexStatus.total_files} files`
                : ' starting…'}
              {demoIndexStatus && demoIndexStatus.embeddings_written > 0
                && ` · ${demoIndexStatus.embeddings_written.toLocaleString()} embeddings`}
            </p>
            {demoIndexStatus?.current_file && (
              <p className="mt-1 truncate text-zinc-500" title={demoIndexStatus.current_file}>
                {demoIndexStatus.current_file}
              </p>
            )}
          </div>
        )}
        {demoPhase === 'testing' && (
          <p className="mt-3 text-sm text-violet-300/90">Running retrieval benchmark on the new index…</p>
        )}
        {demoError && (
          <div className="mt-3 rounded-lg border border-red-900/60 bg-red-950/40 px-3 py-2 text-sm text-red-200" role="alert">
            {demoError}
          </div>
        )}
        {demoResult && (
          <div className="mt-4 rounded-xl border border-zinc-800 bg-zinc-900/40 overflow-hidden">
            <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-zinc-800 px-4 py-3">
              <h4 className="text-sm font-medium text-zinc-300">Results</h4>
              <p className="text-sm text-zinc-400 text-right max-w-sm">
                <span className="text-emerald-400 font-medium tabular-nums">{(demoResult.recall * 100).toFixed(1)}%</span>
                {' '}
                in top-
                {demoResult.top_k}
                {' '}
                (
                {demoResult.pass_count}
                /
                {demoResult.case_count}
                ) ·
                rank scan depth
                {' '}
                {demoResult.search_rank_depth.toLocaleString()}
                {' '}
                / ntotal
                {' '}
                {demoResult.ntotal.toLocaleString()}
                {' '}
                · spec v
                {demoResult.spec_version}
              </p>
            </div>
            {demoResult.count_not_in_index > 0 && (
              <p className="px-4 py-2 text-sm text-amber-200/95 bg-amber-950/35 border-b border-amber-900/50">
                <span className="font-medium">{demoResult.count_not_in_index} of {demoResult.case_count} expected file patterns are not in the current index</span>
                {' '}
                (metadata scan). The benchmark looks for substrings like
                {' '}
                <code className="text-amber-100/90">00_cat</code>
                , … in indexed paths. Point the indexer at
                {' '}
                <code className="text-amber-100/90">data/demo_corpus</code>
                {' '}
                and use
                {' '}
                <span className="text-amber-100/90">Replace entire index</span>
                {' '}
                if you need a clean demo-only run, then
                {' '}
                <span className="text-amber-100/90">re-run the test</span>
                .
              </p>
            )}
            {demoResult.spec_description && (
              <p className="px-4 py-2 text-xs text-zinc-500 border-b border-zinc-800/80">
                {demoResult.spec_description}
              </p>
            )}
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left min-w-[48rem]">
                <thead>
                  <tr className="border-b border-zinc-800 text-zinc-500">
                    <th className="px-4 py-2 font-medium">Label</th>
                    <th className="px-4 py-2 font-medium">Query</th>
                    <th className="px-4 py-2 font-medium">Expect</th>
                    <th className="px-4 py-2 font-medium">Status</th>
                    <th className="px-4 py-2 font-medium text-right">Rank</th>
                    <th className="px-4 py-2 font-medium text-right">Score</th>
                    <th className="px-4 py-2 font-medium text-right">ms</th>
                  </tr>
                </thead>
                <tbody className="text-zinc-200">
                  {demoResult.cases.map((c, i) => {
                    let status: string
                    let statusClass = 'text-zinc-400'
                    if (c.in_top_k) {
                      status = 'In top-k'
                      statusClass = 'text-emerald-400/95'
                    } else if (!c.expected_in_index) {
                      status = 'Not in index'
                      statusClass = 'text-rose-400/90'
                    } else if (c.rank != null) {
                      status = `Below top-${demoResult.top_k}`
                      statusClass = 'text-amber-400/90'
                    } else {
                      status = 'No match'
                      statusClass = 'text-amber-400/90'
                    }
                    return (
                      <tr
                        key={i + c.path_includes + c.query}
                        className="border-b border-zinc-800/70"
                      >
                        <td className="px-4 py-2 align-top text-zinc-300">{c.label}</td>
                        <td className="px-4 py-2 align-top text-zinc-400 max-w-[12rem]">{c.query}</td>
                        <td className="px-4 py-2 align-top text-zinc-500 font-mono text-xs max-w-[8rem] break-all">{c.path_includes}</td>
                        <td className="px-4 py-2 align-top text-xs max-w-[10rem]">
                          <span className={`font-medium ${statusClass}`}>{status}</span>
                          {c.note && (
                            <p className="text-zinc-500 mt-1 leading-snug" title={c.note ?? undefined}>
                              {c.note}
                            </p>
                          )}
                        </td>
                        <td
                          className={`px-4 py-2 text-right tabular-nums align-top ${
                            c.in_top_k ? 'text-emerald-400' : c.expected_in_index ? 'text-amber-400/90' : 'text-zinc-500'
                          }`}
                        >
                          {c.rank ?? '—'}
                        </td>
                        <td className="px-4 py-2 text-right tabular-nums text-zinc-300 align-top">
                          {c.best_score != null ? (c.best_score * 100).toFixed(1) : '—'}
                          {c.best_score != null && '%'}
                        </td>
                        <td className="px-4 py-2 text-right tabular-nums text-zinc-500 align-top">
                          {c.latency_ms.toFixed(0)}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
            {demoResult.ntotal === 0 && (
              <p className="px-4 py-3 text-xs text-amber-300/90 border-t border-zinc-800">
                Index is empty — build the index for your demo folder first, then re-run.
              </p>
            )}
          </div>
        )}
      </section>

      <section className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5 space-y-4">
        <h3 className="text-sm font-medium text-zinc-400 mb-1">Search latency + random baselines</h3>
        <div className="flex flex-col gap-4 sm:flex-row sm:flex-wrap sm:items-end">
          <label className="flex flex-col gap-1 text-xs text-zinc-400">
            Iterations
            <input
              type="number"
              min={1}
              max={500}
              value={iterations}
              onChange={(e) => setIterations(Number(e.target.value))}
              className="w-28 rounded-lg border border-zinc-700 bg-zinc-950 px-2 py-2 text-sm text-white"
            />
          </label>
          <label className="flex flex-col gap-1 text-xs text-zinc-400">
            Top-K
            <select
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              className="rounded-lg border border-zinc-700 bg-zinc-950 px-2 py-2 text-sm text-zinc-200"
            >
              {[5, 10, 12, 20].map((k) => (
                <option key={k} value={k}>{k}</option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-xs text-zinc-400">
            Media filter
            <select
              value={mediaFilter}
              onChange={(e) => setMediaFilter(e.target.value as typeof mediaFilter)}
              className="rounded-lg border border-zinc-700 bg-zinc-950 px-2 py-2 text-sm text-zinc-200"
            >
              <option value="both">Images & videos</option>
              <option value="images">Images only</option>
              <option value="videos">Videos only</option>
            </select>
          </label>
          <button
            type="button"
            onClick={runBenchmark}
            disabled={loading}
            className="rounded-lg bg-violet-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-violet-500 disabled:opacity-50 disabled:cursor-not-allowed sm:ml-auto"
          >
            {loading ? 'Running…' : 'Run benchmark'}
          </button>
        </div>
        {error && (
          <div className="rounded-lg border border-red-900/60 bg-red-950/40 px-3 py-2 text-sm text-red-200" role="alert">
            {error}
          </div>
        )}
      </section>

      {result && (
        <section className="space-y-6">
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 overflow-hidden">
            <h3 className="text-sm font-medium text-zinc-400 px-4 py-3 border-b border-zinc-800">Latency (encode + search per query)</h3>
            <dl className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-4 text-sm">
              <div>
                <dt className="text-zinc-500">Mean</dt>
                <dd className="text-white tabular-nums">{formatMs(result.latency_mean_s)}</dd>
              </div>
              <div>
                <dt className="text-zinc-500">p50</dt>
                <dd className="text-white tabular-nums">{formatMs(result.latency_p50_s)}</dd>
              </div>
              <div>
                <dt className="text-zinc-500">p95</dt>
                <dd className="text-white tabular-nums">{formatMs(result.latency_p95_s)}</dd>
              </div>
              <div>
                <dt className="text-zinc-500">Approx QPS</dt>
                <dd className="text-white tabular-nums">{result.qps.toFixed(2)}</dd>
              </div>
            </dl>
            <p className="px-4 pb-3 text-xs text-zinc-500">
              Index size
              {' '}
              <span className="text-zinc-300 tabular-nums">{result.ntotal.toLocaleString()}</span>
              {' '}
              vectors ·
              {' '}
              {result.iterations}
              {' '}
              timed iterations · top_k=
              {result.top_k}
              {' '}
              ·
              {' '}
              {result.media_filter}
            </p>
          </div>

          <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 overflow-hidden">
            <h3 className="text-sm font-medium text-zinc-400 px-4 py-3 border-b border-zinc-800">
              Retrieval strength (mean top-
              {result.top_k}
              {' '}
              cosine × 100 for each method)
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead>
                  <tr className="border-b border-zinc-800 text-zinc-500">
                    <th className="px-4 py-2 font-medium">Method</th>
                    <th className="px-4 py-2 font-medium text-right">Mean score</th>
                    <th className="px-4 py-2 font-medium text-right">%</th>
                  </tr>
                </thead>
                <tbody className="text-zinc-200">
                  <tr className="border-b border-zinc-800/80 bg-violet-950/20">
                    <td className="px-4 py-2.5">CLIP — natural queries</td>
                    <td className="px-4 py-2.5 text-right tabular-nums">{result.semantic_mean_topk.toFixed(4)}</td>
                    <td className="px-4 py-2.5 text-right tabular-nums text-emerald-400/90">
                      {(result.semantic_mean_topk * 100).toFixed(1)}
                      %
                    </td>
                  </tr>
                  <tr className="border-b border-zinc-800/80">
                    <td className="px-4 py-2.5">Random corpus vectors (same query)</td>
                    <td className="px-4 py-2.5 text-right tabular-nums">{result.random_corpus_mean_topk.toFixed(4)}</td>
                    <td className="px-4 py-2.5 text-right tabular-nums">
                      {(result.random_corpus_mean_topk * 100).toFixed(1)}
                      %
                    </td>
                  </tr>
                  <tr className="border-b border-zinc-800/80">
                    <td className="px-4 py-2.5">Gibberish text queries</td>
                    <td className="px-4 py-2.5 text-right tabular-nums">{result.gibberish_mean_topk.toFixed(4)}</td>
                    <td className="px-4 py-2.5 text-right tabular-nums">
                      {(result.gibberish_mean_topk * 100).toFixed(1)}
                      %
                    </td>
                  </tr>
                  <tr>
                    <td className="px-4 py-2.5">Random unit query vector</td>
                    <td className="px-4 py-2.5 text-right tabular-nums">{result.random_query_unit_mean_topk.toFixed(4)}</td>
                    <td className="px-4 py-2.5 text-right tabular-nums">
                      {(result.random_query_unit_mean_topk * 100).toFixed(1)}
                      %
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div className="px-4 py-3 border-t border-zinc-800 text-xs text-zinc-400 space-y-1">
              <p>
                <span className="text-zinc-300">Semantic / random corpus:</span>
                {' '}
                <span className="text-white tabular-nums">{result.semantic_over_random_corpus.toFixed(2)}×</span>
                {' '}
                — how much stronger real queries align vs unrelated frames from your library.
              </p>
              <p>
                <span className="text-zinc-300">Semantic / gibberish:</span>
                {' '}
                <span className="text-white tabular-nums">{result.semantic_over_gibberish.toFixed(2)}×</span>
              </p>
            </div>
          </div>
        </section>
      )}
    </main>
  )
}
