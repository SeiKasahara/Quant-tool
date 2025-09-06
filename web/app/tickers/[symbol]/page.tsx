'use client'

import { useParams } from 'next/navigation'
import useSWR from 'swr'
import { getTickerSignals, getTickerPrices } from '@/lib/api'
import { formatDate, formatPercentage, getDirectionColor } from '@/lib/utils'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import Link from 'next/link'

export default function TickerPage() {
  const params = useParams()
  const symbol = params.symbol as string
  
  const { data: signalsData, error: signalsError } = useSWR(
    ['ticker-signals', symbol],
    () => getTickerSignals(symbol)
  )
  
  const { data: priceData, error: priceError } = useSWR(
    ['ticker-prices', symbol],
    () => getTickerPrices(symbol)
  )
  
  if (signalsError || priceError) {
    return (
      <div className="text-center py-8">
        <p className="text-red-600">Failed to load ticker data</p>
      </div>
    )
  }
  
  if (!signalsData || !priceData) {
    return (
      <div className="flex justify-center items-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
      </div>
    )
  }
  
  // Add signal markers to price data
  const pricesWithSignals = priceData.prices.map(price => {
    const signal = signalsData.signals.find(s => 
      new Date(s.signal_time).toDateString() === new Date(price.ts).toDateString()
    )
    return {
      ...price,
      signal: signal ? signal.confidence : null
    }
  })
  
  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="bg-card rounded-lg shadow p-6">
        <h1 className="text-3xl font-bold mb-2">{symbol.toUpperCase()}</h1>
        {signalsData.company && (
          <p className="text-lg text-muted-foreground">{signalsData.company}</p>
        )}
        <p className="text-sm text-muted-foreground mt-2">
          {signalsData.total} signals detected
        </p>
      </div>
      
      <div className="bg-card rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">
          Price Chart
          {priceData.is_mock && (
            <span className="ml-2 text-sm text-muted-foreground">(Mock Data)</span>
          )}
        </h3>
        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={pricesWithSignals}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis 
              dataKey="ts" 
              tickFormatter={(ts) => new Date(ts).toLocaleDateString()}
            />
            <YAxis />
            <Tooltip 
              labelFormatter={(ts) => formatDate(ts)}
              formatter={(value: any, name: string) => {
                if (name === 'signal') {
                  return value ? `Signal: ${formatPercentage(value)}` : ''
                }
                return `$${Number(value).toFixed(2)}`
              }}
            />
            <Line 
              type="monotone" 
              dataKey="close" 
              stroke="#8884d8" 
              strokeWidth={2}
              dot={false}
            />
            <Line 
              type="monotone" 
              dataKey="signal" 
              stroke="#ff7300" 
              strokeWidth={0}
              dot={{ r: 6, fill: '#ff7300' }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      
      {signalsData.signals && signalsData.signals.length > 0 && (
        <div className="bg-card rounded-lg shadow overflow-hidden">
          <div className="px-6 py-4 border-b">
            <h3 className="text-lg font-semibold">Recent Signals</h3>
          </div>
          <table className="w-full">
            <thead className="bg-muted">
              <tr>
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
                  Direction
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {signalsData.signals.map((signal: any) => (
                <tr key={signal.id} className="hover:bg-muted/50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    {formatDate(signal.signal_time)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center space-x-2">
                      <div className="w-20 bg-gray-200 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full ${
                            signal.confidence >= 0.8 ? 'bg-green-500' :
                            signal.confidence >= 0.6 ? 'bg-yellow-500' :
                            'bg-red-500'
                          }`}
                          style={{ width: `${signal.confidence * 100}%` }}
                        />
                      </div>
                      <span className="text-sm font-medium">
                        {formatPercentage(signal.confidence)}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm">
                    {signal.label}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`text-sm font-medium ${getDirectionColor(signal.direction)}`}>
                      {signal.direction === 'up' ? '↑ Up' : 
                       signal.direction === 'down' ? '↓ Down' : 
                       '→ Neutral'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}