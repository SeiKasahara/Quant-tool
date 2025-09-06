"use client"
import { useEffect, useRef, useState } from 'react'

type EventCallback = (e: MessageEvent) => void

export function useSSE(url: string, onMessage: EventCallback, fallbackPoll?: () => Promise<any>, pollInterval = 3000) {
  const esRef = useRef<EventSource | null>(null)
  const [connected, setConnected] = useState(false)
  const pollRef = useRef<number | null>(null)

  useEffect(() => {
    let stopped = false
    try {
      const es = new EventSource(url)
      es.onopen = () => { setConnected(true) }
      es.onmessage = onMessage
      es.onerror = () => {
        setConnected(false)
        es.close()
        if (!stopped && fallbackPoll) {
          // start polling fallback
          pollRef.current = window.setInterval(() => {
            fallbackPoll().catch(()=>{})
          }, pollInterval)
        }
      }
      esRef.current = es
    } catch (e) {
      // EventSource not supported or failed - start polling
      if (fallbackPoll) {
        pollRef.current = window.setInterval(() => {
          fallbackPoll().catch(()=>{})
        }, pollInterval)
      }
    }

    return () => {
      stopped = true
      if (esRef.current) { esRef.current.close() }
      if (pollRef.current) { window.clearInterval(pollRef.current) }
    }
  }, [url])

  return { connected }
}
