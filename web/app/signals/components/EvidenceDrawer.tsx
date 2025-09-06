'use client'

import { useEffect, useState } from 'react'
import { Signal, SignalEvidence } from '@/lib/types'
import { getSignalDetails } from '@/lib/api'
import { formatDate, formatPercentage } from '@/lib/utils'
import Link from 'next/link'

interface EvidenceDrawerProps {
  signal: Signal | null
  open: boolean
  onClose: () => void
}

export default function EvidenceDrawer({ signal, open, onClose }: EvidenceDrawerProps) {
  const [details, setDetails] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  
  useEffect(() => {
    if (signal && open) {
      setLoading(true)
      getSignalDetails(signal.id)
        .then(setDetails)
        .catch(console.error)
        .finally(() => setLoading(false))
    }
  }, [signal, open])
  
  if (!open || !signal) return null
  
  return (
    <>
      <div 
        className="fixed inset-0 bg-black bg-opacity-50 z-40"
        onClick={onClose}
      />
      
      <div className="fixed right-0 top-0 h-full w-full md:w-1/2 lg:w-1/3 bg-background shadow-xl z-50 overflow-y-auto">
        <div className="p-6 border-b">
          <div className="flex justify-between items-start">
            <div>
              <h3 className="text-xl font-semibold">Signal Evidence</h3>
              <p className="text-sm text-muted-foreground mt-1">
                {signal.ticker} - {formatDate(signal.signal_time)}
              </p>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
            >
              ✕
            </button>
          </div>
        </div>
        
        <div className="p-6 space-y-6">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-muted-foreground">
                Confidence
              </label>
              <p className="text-lg font-semibold">
                {formatPercentage(signal.confidence)}
              </p>
            </div>
            <div>
              <label className="text-sm font-medium text-muted-foreground">
                Base Score
              </label>
              <p className="text-lg font-semibold">
                {signal.base_score.toFixed(3)}
              </p>
            </div>
          </div>
          
          {loading ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
            </div>
          ) : details ? (
            <>
              {details.meta?.components && (
                <div>
                  <h4 className="font-medium mb-3">Score Components</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span>Source Weight:</span>
                      <span className="font-medium">
                        {details.meta.components.source_weight?.toFixed(2)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Novelty:</span>
                      <span className="font-medium">
                        {details.meta.components.novelty?.toFixed(2)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Event Prior:</span>
                      <span className="font-medium">
                        {details.meta.components.event_prior?.toFixed(2)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Buzz Score:</span>
                      <span className="font-medium">
                        {details.meta.components.buzz_score?.toFixed(2)}
                      </span>
                    </div>
                  </div>
                </div>
              )}
              
              {details.evidence && details.evidence.length > 0 && (
                <div>
                  <h4 className="font-medium mb-3">Evidence Sources</h4>
                  <div className="space-y-3">
                    {details.evidence.map((ev: any, idx: number) => (
                      <div key={idx} className="border rounded-lg p-3">
                        <div className="flex justify-between items-start mb-2">
                          <span className="text-sm font-medium capitalize">
                            {ev.kind}
                          </span>
                          <span className="text-xs text-muted-foreground">
                            Weight: {ev.weight?.toFixed(2)}
                          </span>
                        </div>
                        {ev.document && (
                          <Link
                            href={`/documents/${ev.document.id}`}
                            className="text-sm text-primary hover:underline"
                          >
                            {ev.document.title}
                          </Link>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {details.meta?.requires_second_source && (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                  <p className="text-sm text-yellow-800">
                    ⚠️ Needs 2nd source confirmation
                  </p>
                </div>
              )}
              
              {details.created_at && (
                <div className="text-xs text-muted-foreground">
                  Audit ID: {details.id} | Created: {formatDate(details.created_at)}
                </div>
              )}
            </>
          ) : null}
        </div>
      </div>
    </>
  )
}