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
  status: 'idle' | 'running' | 'completed' | 'failed' | 'cancelled' | string
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

export type LogEntry = {
  ts: number
  level: string
  logger: string
  msg: string
}

export type BenchmarkSearchResponse = {
  ntotal: number
  iterations: number
  top_k: number
  media_filter: string
  latency_mean_s: number
  latency_p50_s: number
  latency_p95_s: number
  qps: number
  semantic_mean_topk: number
  random_corpus_mean_topk: number
  gibberish_mean_topk: number
  random_query_unit_mean_topk: number
  semantic_over_random_corpus: number
  semantic_over_gibberish: number
}

export type DemoRetrievalCaseOut = {
  label: string
  query: string
  path_includes: string
  expected_in_index: boolean
  rank: number | null
  in_top_k: boolean
  best_score: number | null
  latency_ms: number
  note: string | null
}

export type DemoRetrievalResponse = {
  ntotal: number
  top_k: number
  media_filter: string
  spec_version: number
  spec_description: string
  cases: DemoRetrievalCaseOut[]
  pass_count: number
  case_count: number
  recall: number
  search_rank_depth: number
  count_expected_in_index: number
  count_not_in_index: number
}

export type DemoCorpusInfo = {
  index_root_path_for_api: string
  media_root: string
  demo_corpus_absolute: string
  demo_corpus_exists: boolean
}
