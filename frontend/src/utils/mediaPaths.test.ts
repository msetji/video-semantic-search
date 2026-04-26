//unit tests for the mediaPaths utility function to make sure file type detection and URL construction work

import { describe, expect, it } from 'vitest'

import {
  absoluteUrlForMediaPreview,
  isMp4VideoFilePath,
  isRasterImageFilePath,
  previewUsesVideoElement,
} from './mediaPaths'

describe('isRasterImageFilePath', () => {
  it('returns true for common raster extensions', () => {
    expect(isRasterImageFilePath('/a/b/photo.JPG')).toBe(true)
    expect(isRasterImageFilePath('x.webp')).toBe(true)
  })

  it('returns false for non-raster paths', () => {
    expect(isRasterImageFilePath('x.mp4')).toBe(false)
  })
})

describe('isMp4VideoFilePath', () => {

   //case-insensitive
  it('matches mp4 case-insensitively', () => {
    expect(isMp4VideoFilePath('clip.MP4')).toBe(true)
    expect(isMp4VideoFilePath('x.mov')).toBe(false)
  })
})

describe('previewUsesVideoElement', () => {
  it('uses video for kind video or mp4 path', () => {
    expect(
      previewUsesVideoElement({ kind: 'video', path: 'a/b.mp4' }),
    ).toBe(true)
    expect(
      previewUsesVideoElement({ kind: 'image', path: 'a/b.mp4' }),
    ).toBe(true)
    expect(
      previewUsesVideoElement({ kind: 'image', path: 'a/b.jpg' }),
    ).toBe(false)
  })
})

describe('absoluteUrlForMediaPreview', () => {

  //relative URLs get the API base
  it('prefixes relative media URLs with API base', () => {
    expect(
      absoluteUrlForMediaPreview('http://127.0.0.1:8000', '/media/x.jpg'),
    ).toBe('http://127.0.0.1:8000/media/x.jpg')
  })

  //absolute URLs should pass through without being altered
  it('returns absolute URLs unchanged', () => {
    expect(
      absoluteUrlForMediaPreview('http://127.0.0.1:8000', 'https://cdn/x.jpg'),
    ).toBe('https://cdn/x.jpg')
  })
})
