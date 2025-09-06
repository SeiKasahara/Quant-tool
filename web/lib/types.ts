export type Source = {
  kind: string
  id?: number
  title?: string
}

export type Signal = {
  id: number
  ticker: string
  signal_time: string
  confidence: number
  base_score: number
  label?: string
  direction?: 'up' | 'down' | 'neutral'
  decay_seconds?: number
  meta?: any
  sources: Source[]
}

export type SignalEvidence = {
  kind: string
  weight?: number
  details?: any
  document?: {
    id: number
    title: string
    url?: string
    source?: string
    published_at?: string
  }
}

export type Document = {
  id: number
  source: string
  url: string
  title: string
  published_at: string
  fetched_at?: string
  excerpt?: string
  full_text?: string
  html_snapshot_path?: string
  lang?: string
  sentiment?: string
  sentiment_score?: number
  entities?: Array<{ id?: number; name: string; type: string; mentions?: number }>
  events?: Array<any>
  meta?: any
}

export type SignalsResponse = {
  items: Signal[]
  total: number
}

export type SignalDetails = {
  id: number
  ticker?: string
  signal_time?: string
  confidence?: number
  base_score?: number
  label?: string
  direction?: string
  decay_seconds?: number
  meta?: any
  evidence?: SignalEvidence[]
  created_at?: string
}

export type PricePoint = { ts: string; open?: number; high?: number; low?: number; close: number; volume?: number }
export type PriceResponse = { prices: PricePoint[]; is_mock?: boolean }

export type TickerSignalsResponse = { ticker?: string; company?: string; signals: Signal[]; total: number }