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
