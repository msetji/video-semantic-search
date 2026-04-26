import {
  isRasterImageFilePath,
  previewUsesVideoElement,
} from '../utils/mediaPaths'
import type { SearchHit } from '../types'

const API_BASE = import.meta.env.VITE_API_BASE ?? ''

async function revealInExplorer(path: string) {
  try {
    await fetch(`${API_BASE}/api/system/reveal-file`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path }),
    })
  } catch {
    // best-effort — Explorer may still open even if fetch errors
  }
}

//displays the preview element depending on whether the result is a video frame or image
export function MediaPreview({
  hit,
  src,
}: {
  hit: SearchHit
  src: string
}) {

  // for videos, find the right timestamp where the match is found
  if (previewUsesVideoElement(hit)) {
    return (
      <div className="relative h-full w-full group cursor-pointer" onClick={() => revealInExplorer(hit.path)}>
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
        {/* hover overlay */}
        <div className="absolute inset-0 flex items-center justify-center bg-black/0 group-hover:bg-black/40 transition-colors duration-200 pointer-events-none">
          <span className="opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex flex-col items-center gap-1">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-7 w-7 text-white drop-shadow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
            </svg>
            <span className="text-white text-xs font-medium drop-shadow">Show in Explorer</span>
          </span>
        </div>
      </div>
    )
  }

  //for images, just show the image preview
  if (isRasterImageFilePath(hit.path)) {
    return (
      <img src={src} alt="" className="h-full w-full object-cover" loading="lazy" />
    )
  }
  return (
    <div className="flex h-full w-full items-center justify-center bg-zinc-900 text-sm text-zinc-500">
      Preview not available
    </div>
  )
}
