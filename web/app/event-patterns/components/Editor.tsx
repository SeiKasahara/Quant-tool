"use client"
import React, { useEffect, useState } from 'react'
import api from '@/lib/api'

type Patterns = { [k: string]: string[] }

export default function Editor() {
  const [patterns, setPatterns] = useState<Patterns>({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [validationErrors, setValidationErrors] = useState<{ [k: string]: (string | null)[] }>({})

  useEffect(() => {
    let mounted = true
    ;(async () => {
      try {
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000'}/event-patterns`)
        if (!res.ok) throw new Error(await res.text())
        const data = await res.json()
        if (mounted) setPatterns(data || {})
      } catch (e: any) {
        setError(String(e))
      } finally {
        setLoading(false)
      }
    })()
    return () => { mounted = false }
  }, [])

  function setPatternFor(key: string, idx: number, value: string) {
    setPatterns(prev => ({ ...prev, [key]: prev[key].map((v, i) => i === idx ? value : v) }))
    // validate this single pattern immediately
    try {
      // empty string is considered invalid
      if (!value || value.trim() === '') throw new Error('Empty pattern')
      // try construct RegExp to validate syntax
      // Note: do not set flags here; user can include them in pattern as needed
      // but RegExp constructor will throw on invalid patterns
      // eslint-disable-next-line no-new
      new RegExp(value)
      setValidationErrors(prev => ({ ...prev, [key]: (prev[key] || []).map((e, i) => i === idx ? null : e) }))
    } catch (e: any) {
      setValidationErrors(prev => ({ ...prev, [key]: (prev[key] || []).map((er, i) => i === idx ? String(e.message || e) : er) }))
    }
  }

  function addPattern(key: string) {
  setPatterns(prev => ({ ...prev, [key]: [...(prev[key] || []), ''] }))
  setValidationErrors(prev => ({ ...prev, [key]: [...(prev[key] || []).map(() => null), 'Empty pattern'] }))
  }

  function removePattern(key: string, idx: number) {
  setPatterns(prev => ({ ...prev, [key]: prev[key].filter((_, i) => i !== idx) }))
  setValidationErrors(prev => ({ ...prev, [key]: (prev[key] || []).filter((_, i) => i !== idx) }))
  }

  function addEvent() {
    const key = prompt('New event key (snake_case)')
    if (!key) return
    setPatterns(prev => ({ ...prev, [key]: [''] }))
    setValidationErrors(prev => ({ ...prev, [key]: ['Empty pattern'] }))
  }

  async function save() {
    // run full validation before save
    setError(null)
    const errors: { [k: string]: (string | null)[] } = {}
    let hasError = false
    Object.entries(patterns).forEach(([k, arr]) => {
      errors[k] = arr.map(p => {
        if (!p || p.trim() === '') {
          hasError = true
          return 'Empty pattern'
        }
        try {
          // eslint-disable-next-line no-new
          new RegExp(p)
          return null
        } catch (e: any) {
          hasError = true
          return String(e.message || e)
        }
      })
    })
    setValidationErrors(errors)
    if (hasError) {
      setError('Fix invalid patterns before saving')
      return
    }

    setSaving(true)
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000'}/event-patterns`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(patterns)
      })
      if (!res.ok) {
        const txt = await res.text()
        // try parse structured JSON error from backend
        try {
          const body = JSON.parse(txt)
          if (body && body.detail && body.detail.validation_errors) {
            setValidationErrors(body.detail.validation_errors)
            setError('Server-side validation errors; fix before saving')
            return
          }
        } catch (_) {
          // fall through
        }
        throw new Error(txt)
      }
      alert('Saved')
    } catch (e: any) {
      setError(String(e))
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <div>Loading...</div>

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold">Event Patterns (Advanced)</h2>
        <div>
          <button onClick={addEvent} className="mr-2 btn">Add Event</button>
          <button onClick={save} disabled={saving} className="btn btn-primary">{saving ? 'Saving...' : 'Save'}</button>
        </div>
      </div>

      {error && <div className="text-red-600 mb-4">{error}</div>}

      <div className="grid gap-6">
        {Object.entries(patterns).map(([key, arr]) => (
          <div key={key} className="p-4 border rounded">
            <div className="flex items-center justify-between mb-2">
              <strong>{key}</strong>
              <button onClick={() => { const ok = confirm('Remove event ' + key + '?'); if (ok) { const copy = { ...patterns }; delete copy[key]; setPatterns(copy); } }} className="text-sm text-red-600">Remove</button>
            </div>
            {arr.map((pat, i) => (
              <div key={i} className="mb-2">
                <textarea value={pat} onChange={e => setPatternFor(key, i, e.target.value)} className="w-full p-2 border rounded h-16" />
                {validationErrors[key] && validationErrors[key][i] && (
                  <div className="text-sm text-red-600 mt-1">{validationErrors[key][i]}</div>
                )}
                <div className="flex justify-end mt-1">
                  <button onClick={() => removePattern(key, i)} className="text-sm text-red-600">Remove</button>
                </div>
              </div>
            ))}
            <div>
              <button onClick={() => addPattern(key)} className="text-sm">Add pattern</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
