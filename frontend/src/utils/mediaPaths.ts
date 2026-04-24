const RASTER_IMAGE_FILE_EXTENSION_PATTERN = /\.(jpe?g|png|webp)$/i

export function isRasterImageFilePath(filePath: string): boolean {
  return RASTER_IMAGE_FILE_EXTENSION_PATTERN.test(filePath)
}

export function isMp4VideoFilePath(filePath: string): boolean {
  return /\.mp4$/i.test(filePath)
}

export function previewUsesVideoElement(hit: {
  kind: string
  path: string
}): boolean {
  return hit.kind === 'video' || isMp4VideoFilePath(hit.path)
}

export function absoluteUrlForMediaPreview(
  apiBaseWithoutTrailingSlash: string,
  mediaUrlFromServer: string,
): string {
  if (apiBaseWithoutTrailingSlash && mediaUrlFromServer.startsWith('/')) {
    return `${apiBaseWithoutTrailingSlash}${mediaUrlFromServer}`
  }
  return mediaUrlFromServer
}
