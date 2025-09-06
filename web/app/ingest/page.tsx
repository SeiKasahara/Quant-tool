"use client"
import { useEffect, useState } from 'react'
import { useSSE } from '@/lib/useSSE'

export default function IngestPage() {
  const [events, setEvents] = useState<any[]>([])

  const onMessage = (e: MessageEvent) => {
    try {
      const payload = JSON.parse(e.data)
      setEvents(prev => [payload].concat(prev).slice(0, 200))
    } catch (err) {}
  }

  const fallbackPoll = async () => {
    // In fallback, we could call /ingest/runs; for MVP just push a heartbeat
    setEvents(prev => [{ type: 'heartbeat', at: new Date().toISOString() }].concat(prev).slice(0,200))
  }

  const { connected } = useSSE(`/ingest/stream`, onMessage, fallbackPoll, 3000)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Ingest Runs</h2>
        <div className="text-sm">{connected ? 'SSE connected' : 'Polling fallback'}</div>
      </div>

      <div className="bg-card rounded p-4">
        <h3 className="font-semibold mb-2">Recent Events</h3>
        <div className="max-h-96 overflow-y-auto">
          {events.length === 0 && <div className="text-sm text-muted-foreground">No events yet</div>}
          {events.map((ev, idx) => (
            <div key={idx} className="p-2 border-b last:border-b-0">
              <div className="text-xs text-muted-foreground">{ev.type || ev.event || 'event'} • {ev.at || ev.ts || ''}</div>
              <div className="text-sm">{ev.message || JSON.stringify(ev.payload || ev)}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
