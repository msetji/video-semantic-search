import {
  isRasterImageFilePath,
  previewUsesVideoElement,
} from '../utils/mediaPaths'
import type { SearchHit } from '../types'

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
