'use client'

import { useState } from 'react'

interface FiltersProps {
  filters: {
    q: string
    min_confidence: number
    date_from: string
    date_to: string
  }
  onChange: (filters: any) => void
}

export default function Filters({ filters, onChange }: FiltersProps) {
  const [localFilters, setLocalFilters] = useState(filters)
  
  const handleChange = (key: string, value: any) => {
    const newFilters = { ...localFilters, [key]: value }
    setLocalFilters(newFilters)
    onChange(newFilters)
  }
  
  return (
    <div className="bg-card rounded-lg shadow p-6 space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div>
          <label className="block text-sm font-medium mb-2">
            Ticker/Company Search
          </label>
          <input
            type="text"
            value={localFilters.q}
            onChange={(e) => handleChange('q', e.target.value)}
            placeholder="Search..."
            className="w-full px-3 py-2 border border-input rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium mb-2">
            Min Confidence: {(localFilters.min_confidence * 100).toFixed(0)}%
          </label>
          <input
            type="range"
            min="0"
            max="100"
            value={localFilters.min_confidence * 100}
            onChange={(e) => handleChange('min_confidence', Number(e.target.value) / 100)}
            className="w-full"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium mb-2">
            Date From
          </label>
          <input
            type="date"
            value={localFilters.date_from}
            onChange={(e) => handleChange('date_from', e.target.value)}
            className="w-full px-3 py-2 border border-input rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium mb-2">
            Date To
          </label>
          <input
            type="date"
            value={localFilters.date_to}
            onChange={(e) => handleChange('date_to', e.target.value)}
            className="w-full px-3 py-2 border border-input rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>
      </div>
    </div>
  )
}