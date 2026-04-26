import { useEffect, useRef, useState } from 'react'
import type { LogEntry } from '../types'

const API_BASE = import.meta.env.VITE_API_BASE ?? ''

const LEVEL_STYLES: Record<string, { row: string; badge: string }> = {
  CRITICAL: { row: 'text-red-300',  badge: 'bg-red-900/60 text-red-300' },
  ERROR:    { row: 'text-red-400',  badge: 'bg-red-900/40 text-red-400' },
  WARNING:  { row: 'text-amber-400', badge: 'bg-amber-900/40 text-amber-400' },
  INFO:     { row: 'text-zinc-300', badge: 'bg-zinc-800 text-zinc-400' },
  DEBUG:    { row: 'text-zinc-500', badge: 'bg-zinc-900 text-zinc-600' },
}

function levelStyle(level: string) {
  return LEVEL_STYLES[level] ?? LEVEL_STYLES.DEBUG
}

export function Logs() {
  const [entries, setEntries] = useState<LogEntry[]>([])
  const [filter, setFilter] = useState('ALL')
  const [autoScroll, setAutoScroll] = useState(true)
  const [connected, setConnected] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    let cancelled = false

    async function poll() {
      try {
        const res = await fetch(`${API_BASE}/api/logs`)
        if (!cancelled && res.ok) {
          const data = await res.json()
          setEntries(data.logs)
          setConnected(true)
        }
      } catch {
        if (!cancelled) setConnected(false)
      }
    }

    poll()
    const id = setInterval(poll, 2000)
    return () => {
      cancelled = true
      clearInterval(id)
    }
  }, [])

  useEffect(() => {
    if (autoScroll && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [entries, autoScroll])

  const filtered = filter === 'ALL'
    ? entries
    : entries.filter(e => e.level === filter)

  const counts = entries.reduce<Record<string, number>>((acc, e) => {
    acc[e.level] = (acc[e.level] ?? 0) + 1
    return acc
  }, {})

  return (
    <div className="mx-auto max-w-6xl px-4 py-6 space-y-4">
      {/* header row */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <h2 className="text-sm font-semibold text-zinc-200">System Logs</h2>
          <span className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium ${connected ? 'bg-emerald-900/40 text-emerald-400' : 'bg-zinc-800 text-zinc-500'}`}>
            <span className={`h-1.5 w-1.5 rounded-full ${connected ? 'bg-emerald-400' : 'bg-zinc-600'}`} />
            {connected ? 'Live' : 'Disconnected'}
          </span>
          {/* level pill counts */}
          {(['ERROR', 'WARNING'] as const).map(lvl =>
            (counts[lvl] ?? 0) > 0 ? (
              <span key={lvl} className={`rounded px-1.5 py-0.5 text-xs font-medium ${levelStyle(lvl).badge}`}>
                {counts[lvl]} {lvl.toLowerCase()}
              </span>
            ) : null
          )}
        </div>

        <div className="flex items-center gap-3">
          <select
            value={filter}
            onChange={e => setFilter(e.target.value)}
            className="rounded border border-zinc-700 bg-zinc-900 px-2 py-1 text-xs text-zinc-300 focus:border-violet-500 focus:outline-none"
          >
            <option value="ALL">All levels</option>
            <option value="ERROR">ERROR</option>
            <option value="WARNING">WARNING</option>
            <option value="INFO">INFO</option>
            <option value="DEBUG">DEBUG</option>
          </select>
          <label className="flex cursor-pointer items-center gap-1.5 text-xs text-zinc-400">
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={e => setAutoScroll(e.target.checked)}
              className="accent-violet-500"
            />
            Auto-scroll
          </label>
        </div>
      </div>

      {/* log pane */}
      <div className="h-[62vh] overflow-y-auto rounded-lg border border-zinc-800 bg-zinc-950 p-3 font-mono text-xs leading-relaxed">
        {filtered.length === 0 ? (
          <p className="italic text-zinc-600">
            {entries.length === 0 ? 'Waiting for log entries…' : 'No entries match the current filter.'}
          </p>
        ) : (
          filtered.map((entry, i) => {
            const d = new Date(entry.ts * 1000)
            const time = d.toLocaleTimeString('en-US', {
              hour12: false,
              hour: '2-digit',
              minute: '2-digit',
              second: '2-digit',
            })
            const { row, badge } = levelStyle(entry.level)
            const shortLogger = entry.logger.split('.').at(-1) ?? entry.logger

            return (
              <div key={i} className={`flex gap-2 py-[2px] ${row}`}>
                <span className="shrink-0 text-zinc-600">{time}</span>
                <span className={`shrink-0 rounded px-1 py-px text-[10px] font-semibold uppercase leading-[14px] ${badge}`}>
                  {entry.level.slice(0, 4)}
                </span>
                <span className="w-28 shrink-0 truncate text-zinc-500" title={entry.logger}>
                  {shortLogger}
                </span>
                <span className="min-w-0 break-words">{entry.msg}</span>
              </div>
            )
          })
        )}
        <div ref={bottomRef} />
      </div>

      <p className="text-right text-xs text-zinc-600">
        {filtered.length} / {entries.length} entries
      </p>
    </div>
  )
}
