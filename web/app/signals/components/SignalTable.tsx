'use client'

import { Signal } from '@/lib/types'
import { formatDate, formatPercentage, getDirectionColor, getConfidenceColor } from '@/lib/utils'
import Link from 'next/link'

interface SignalTableProps {
  signals: Signal[]
  onSignalClick: (signal: Signal) => void
}

export default function SignalTable({ signals, onSignalClick }: SignalTableProps) {
  if (signals.length === 0) {
    return (
      <div className="bg-card rounded-lg shadow p-8 text-center">
        <p className="text-muted-foreground">No signals found</p>
      </div>
    )
  }
  
  return (
    <div className="bg-card rounded-lg shadow overflow-hidden">
      <table className="w-full">
        <thead className="bg-muted">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Ticker
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Time
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Confidence
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Label
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Sources
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {signals.map((signal) => (
            <tr
              key={signal.id}
              onClick={() => onSignalClick(signal)}
              className="hover:bg-muted/50 cursor-pointer transition-colors"
            >
              <td className="px-6 py-4 whitespace-nowrap">
                <Link 
                  href={`/tickers/${signal.ticker}`}
                  onClick={(e) => e.stopPropagation()}
                  className="font-medium text-primary hover:underline"
                >
                  {signal.ticker}
                </Link>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm">
                {formatDate(signal.signal_time)}
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="flex items-center space-x-2">
                  <div className="w-24 bg-gray-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${getConfidenceColor(signal.confidence)}`}
                      style={{ width: `${signal.confidence * 100}%` }}
                    />
                  </div>
                  <span className="text-sm font-medium">
                    {formatPercentage(signal.confidence)}
                  </span>
                </div>
              </td>
              <td className="px-6 py-4">
                <div className="flex items-center space-x-2">
                  <span className={`text-sm font-medium ${getDirectionColor(signal.direction)}`}>
                    {signal.direction === 'up' ? '↑' : signal.direction === 'down' ? '↓' : '→'}
                  </span>
                  <span className="text-sm">{signal.label}</span>
                </div>
              </td>
              <td className="px-6 py-4 text-sm">
                {signal.sources.map((source, idx) => (
                  <div key={idx} className="truncate max-w-xs">
                    {source.title}
                  </div>
                ))}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}