export type SearchHit = {
  path: string
  kind: string
  time_sec: number | null
  score: number
  media_url: string
}

export type SearchResponse = {
  query: string
  results: SearchHit[]
}

export type LibraryFile = {
  name: string
  path: string
  kind: 'image' | 'video' | string
  frame_count: number
  duration_sec: number | null
}

export type LibraryDirectory = {
  name: string
  path: string
  file_count: number
  embedding_count: number
  files: LibraryFile[]
}

export type LibraryResponse = {
  total_files: number
  total_embeddings: number
  directories: LibraryDirectory[]
}

export type IndexLastResult = {
  root: string
  images_indexed: number
  videos_indexed: number
  embeddings: number
}

export type IndexStatus = {
  status: 'idle' | 'running' | 'completed' | 'failed' | string
  detail: string | null
  error: string | null
  embeddings_written: number
  total_files: number
  files_done: number
  current_file: string | null
  started_at: number | null
  finished_at: number | null
  last_result: IndexLastResult | null
}
