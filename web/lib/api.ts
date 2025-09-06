import { SignalsResponse, SignalDetails, Document, PriceResponse, TickerSignalsResponse, Signal } from '@/lib/types'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || process.env.WEB_PUBLIC_API || 'http://localhost:8000'

async function jsonFetch<T>(url: string, opts: RequestInit = {}): Promise<T> {
  const res = await fetch(url, { ...opts })
  if (!res.ok) throw new Error(`HTTP ${res.status} ${res.statusText}`)
  return res.json()
}

function toRelativeNextPath(p: string) {
  // Next's app directory routes are served under /api when running dev/edge; use /api fallback
  if (p.startsWith('/app/')) return p.replace('/app', '')
  return p
}

export async function getSignals(filters: any = {}): Promise<SignalsResponse> {
  const q = new URLSearchParams()
  Object.entries(filters || {}).forEach(([k, v]) => { if (v !== undefined && v !== '') q.set(k, String(v)) })

  // Try backend first
  try {
    const url = `${API_BASE}/signals?${q.toString()}`
    const res = await jsonFetch<{ items: any[]; total: number }>(url)
    // Normalize to frontend types
    const items: Signal[] = res.items.map(it => ({
      id: it.id,
      ticker: it.ticker,
      signal_time: (it.signal_time as string) || it.signal_time,
      confidence: it.confidence,
      base_score: it.base_score,
      label: it.label,
      direction: it.direction as any,
      sources: (it.sources || []).map((s: any) => ({ kind: s.kind, id: s.id, title: s.title }))
    }))
    return { items, total: res.total }
  } catch (e) {
    // Fallback to next local mock route
    const url = toRelativeNextPath(`/app/signals/api?${q.toString()}`)
    return await jsonFetch(url)
  }
}

export async function getSignalDetails(id: number): Promise<SignalDetails> {
  try {
    const url = `${API_BASE}/signals/${id}`
    return await jsonFetch(url)
  } catch (e) {
    const url = toRelativeNextPath(`/api/signals/${id}`)
    return await jsonFetch(url)
  }
}

export async function getDocument(id: number): Promise<Document> {
  try {
    const url = `${API_BASE}/documents/${id}`
    return await jsonFetch(url)
  } catch (e) {
    const url = toRelativeNextPath(`/api/documents/${id}`)
    return await jsonFetch(url)
  }
}

export async function getTickerPrices(symbol: string): Promise<PriceResponse> {
  try {
    const url = `${API_BASE}/tickers/${symbol}/prices`
    const res = await jsonFetch<any>(url)
    // Normalize times to ISO strings
    const prices = (res.prices || []).map((p: any) => ({ ts: (p.ts instanceof Object ? new Date(p.ts).toISOString() : p.ts), close: p.close }))
    return { prices, is_mock: !!res.is_mock }
  } catch (e) {
    // Fallback: generate mock series
    const now = Date.now()
    const prices = Array.from({ length: 30 }).map((_, i) => ({ ts: new Date(now - (29 - i) * 24 * 3600 * 1000).toISOString(), close: 100 + i + Math.random() * 3 }))
    return { prices, is_mock: true }
  }
}

export async function getTickerSignals(symbol: string): Promise<TickerSignalsResponse> {
  try {
    const url = `${API_BASE}/tickers/${symbol}/signals`
    return await jsonFetch(url)
  } catch (e) {
    // Fallback mock
    return { signals: [{ id: 1, ticker: symbol, signal_time: new Date().toISOString(), confidence: 0.75, base_score: 0.6, label: 'mock', direction: 'up', sources: [] }], total: 1, company: symbol }
  }
}

export default {
  getSignals,
  getSignalDetails,
  getDocument,
  getTickerPrices,
  getTickerSignals
}
