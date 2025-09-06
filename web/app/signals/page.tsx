'use client'

import { useState, useEffect } from 'react'
import useSWR from 'swr'
import { Signal } from '@/lib/types'
import { getSignals } from '@/lib/api'
import Filters from './components/Filters'
import SignalTable from './components/SignalTable'
import EvidenceDrawer from './components/EvidenceDrawer'

export default function SignalsPage() {
  const [filters, setFilters] = useState({
    q: '',
    min_confidence: 0.6,
    date_from: '',
    date_to: ''
  })
  
  const [selectedSignal, setSelectedSignal] = useState<Signal | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  
  const { data, error, mutate } = useSWR(
    ['signals', filters],
    () => getSignals(filters),
    {
      refreshInterval: 10000, // Poll every 10 seconds
      revalidateOnFocus: true
    }
  )
  
  const handleSignalClick = (signal: Signal) => {
    setSelectedSignal(signal)
    setDrawerOpen(true)
  }
  
  const handleFilterChange = (newFilters: typeof filters) => {
    setFilters(newFilters)
  }
  
  if (error) {
    return (
      <div className="text-center py-8">
        <p className="text-red-600">Failed to load signals</p>
        <button 
          onClick={() => mutate()}
          className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Retry
        </button>
      </div>
    )
  }
  
  if (!data) {
    return (
      <div className="flex justify-center items-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
      </div>
    )
  }
  
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-3xl font-bold">Signals</h2>
        <div className="text-sm text-muted-foreground">
          {data.total} signals found
        </div>
      </div>
      
      <Filters 
        filters={filters}
        onChange={handleFilterChange}
      />
      
      <SignalTable 
        signals={data.items}
        onSignalClick={handleSignalClick}
      />
      
      <EvidenceDrawer
        signal={selectedSignal}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
      />
    </div>
  )
}