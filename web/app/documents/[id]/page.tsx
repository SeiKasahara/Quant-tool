'use client'

import { useParams } from 'next/navigation'
import useSWR from 'swr'
import { getDocument, getTickerPrices } from '@/lib/api'
import { formatDate, formatPercentage } from '@/lib/utils'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import Link from 'next/link'

export default function DocumentPage() {
  const params = useParams()
  const id = Number(params.id)
  
  const { data: doc, error } = useSWR(
    ['document', id],
    () => getDocument(id)
  )
  
  // Get price data for the first ticker mentioned
  const ticker = doc?.meta?.tickers?.[0]
  const { data: priceData } = useSWR(
    ticker ? ['prices', ticker] : null,
    () => getTickerPrices(ticker)
  )
  
  if (error) {
    return (
      <div className="text-center py-8">
        <p className="text-red-600">Failed to load document</p>
      </div>
    )
  }
  
  if (!doc) {
    return (
      <div className="flex justify-center items-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
      </div>
    )
  }
  
  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="bg-card rounded-lg shadow p-6">
        <h1 className="text-2xl font-bold mb-2">{doc.title}</h1>
        <div className="flex flex-wrap gap-4 text-sm text-muted-foreground mb-4">
          <span>Source: {doc.source}</span>
          <span>Published: {formatDate(doc.published_at)}</span>
          <span>Language: {doc.lang}</span>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <div>
            <label className="text-sm font-medium text-muted-foreground">
              Sentiment
            </label>
            <p className="text-lg">
              <span className={`font-semibold ${
                doc.sentiment === 'positive' ? 'text-green-600' : 
                doc.sentiment === 'negative' ? 'text-red-600' : 
                'text-gray-600'
              }`}>
                {doc.sentiment}
              </span>
              <span className="ml-2 text-sm">
                ({formatPercentage(doc.sentiment_score)})
              </span>
            </p>
          </div>
          
          <div>
            <label className="text-sm font-medium text-muted-foreground">
              Novelty Score
            </label>
            <p className="text-lg font-semibold">
              {doc.meta?.novelty ? doc.meta.novelty.toFixed(2) : 'N/A'}
            </p>
          </div>
        </div>
        
        <div className="mb-6">
          <h3 className="font-medium mb-2">Text Excerpt</h3>
          <p className="text-sm text-muted-foreground whitespace-pre-wrap">
            {doc.excerpt}
          </p>
        </div>
        
        <div className="flex gap-4">
          <a
            href={doc.url}
            target="_blank"
            rel="noopener noreferrer"
            className="px-4 py-2 bg-primary text-primary-foreground rounded hover:opacity-90"
          >
            View Original
          </a>
          {doc.html_snapshot_path && (
            <a
              href={`/data/${doc.html_snapshot_path}`}
              target="_blank"
              className="px-4 py-2 border border-input rounded hover:bg-muted"
            >
              View Snapshot
            </a>
          )}
        </div>
      </div>
      
      {doc.entities && doc.entities.length > 0 && (
        <div className="bg-card rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Entities</h3>
          <div className="flex flex-wrap gap-2">
            {doc.entities.map((entity) => (
              <span
                key={entity.id}
                className="px-3 py-1 bg-muted rounded-full text-sm"
              >
                {entity.name} ({entity.type})
              </span>
            ))}
          </div>
        </div>
      )}
      
      {doc.events && doc.events.length > 0 && (
        <div className="bg-card rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Events</h3>
          <div className="space-y-3">
            {doc.events.map((event) => (
              <div key={event.id} className="border rounded-lg p-3">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="font-medium">{event.headline}</p>
                    <p className="text-sm text-muted-foreground">
                      Type: {event.event_type} | Confidence: {formatPercentage(event.confidence)}
                    </p>
                  </div>
                  {event.affected_ticker && (
                    <Link
                      href={`/tickers/${event.affected_ticker}`}
                      className="text-primary hover:underline"
                    >
                      {event.affected_ticker}
                    </Link>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      
      {priceData && priceData.prices && (
        <div className="bg-card rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">
            Price Chart - {ticker}
            {priceData.is_mock && (
              <span className="ml-2 text-sm text-muted-foreground">(Mock Data)</span>
            )}
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={priceData.prices}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="ts" 
                tickFormatter={(ts) => new Date(ts).toLocaleDateString()}
              />
              <YAxis />
              <Tooltip 
                labelFormatter={(ts) => formatDate(ts)}
                formatter={(value: any) => `$${Number(value).toFixed(2)}`}
              />
              <Line 
                type="monotone" 
                dataKey="close" 
                stroke="#8884d8" 
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}