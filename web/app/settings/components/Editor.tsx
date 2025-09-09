"use client"
import React, { useEffect, useState } from 'react'

type Settings = {
  weights: Record<string, number>
  source_weights: Record<string, number>
  event_priors: Record<string, number>
}

export default function Editor(){
  const [settings, setSettings] = useState<Settings | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)
  const [errors, setErrors] = useState<Record<string,string>>({})

  useEffect(() => {
    let mounted = true
    ;(async () => {
      try {
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE || ''}/settings`)
        if (!res.ok) throw new Error('Failed to fetch')
        const body = await res.json()
        if (mounted) setSettings(body)
      } catch (err:any){
        setMsg(String(err?.message || err))
      } finally { if (mounted) setLoading(false) }
    })()
    return () => { mounted = false }
  }, [])

  useEffect(() => {
    // validate whenever settings change
    if (!settings) { setErrors({}); return }
    const errs: Record<string,string> = {}

    // weights: all keys except TAU should be in [0,1]; TAU > 0
    for (const [k, v] of Object.entries(settings.weights)){
      if (k === 'TAU'){
        if (!(typeof v === 'number' && v > 0)) errs[`weights.${k}`] = 'TAU must be > 0'
      } else {
        if (!(typeof v === 'number' && v >= 0 && v <= 1)) errs[`weights.${k}`] = 'Must be between 0 and 1'
      }
    }

    // source_weights: 0..1
    for (const [k, v] of Object.entries(settings.source_weights)){
      if (!(typeof v === 'number' && v >= 0 && v <= 1)) errs[`source_weights.${k}`] = 'Must be between 0 and 1'
    }

    // event_priors: 0..1
    for (const [k, v] of Object.entries(settings.event_priors)){
      if (!(typeof v === 'number' && v >= 0 && v <= 1)) errs[`event_priors.${k}`] = 'Must be between 0 and 1'
    }

    setErrors(errs)
  }, [settings])

  function setNested(path: string, value: number){
    setSettings(prev => {
      if (!prev) return prev
      const copy = JSON.parse(JSON.stringify(prev))
      const keys = path.split('.')
      let cur: any = copy
      for (let i=0;i<keys.length-1;i++) cur = cur[keys[i]]
      cur[keys[keys.length-1]] = value
      return copy
    })
  }

  async function onSave(){
    if (!settings) return
    // prevent save if validation errors
    if (Object.keys(errors).length > 0){
      setMsg('Fix validation errors before saving')
      return
    }
    setSaving(true)
    setMsg(null)
    try{
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE || ''}/settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
      })
      if (!res.ok) {
        const text = await res.text()
        throw new Error(text || 'Save failed')
      }
      setMsg('Saved successfully')
    }catch(err:any){
      setMsg(String(err?.message || err))
    }finally{ setSaving(false) }
  }

  if (loading) return <div>Loading...</div>
  if (!settings) return <div className="text-red-600">Failed to load settings: {msg}</div>

  return (
    <div>
      {msg && <div className="mb-3 text-sm text-slate-700">{msg}</div>}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 border rounded">
          <h3 className="font-semibold mb-2">Weights</h3>
          {Object.entries(settings.weights).map(([k,v]) => (
            <div key={k} className="flex flex-col mb-2">
              <div className="flex items-center gap-2">
                <label className="w-36 text-sm">{k}</label>
                <input type="number" step="0.01" value={v} onChange={e => setNested(`weights.${k}`, Number(e.target.value))} className="px-2 py-1 border rounded w-full" />
              </div>
              {errors[`weights.${k}`] && <div className="text-xs text-red-600 mt-1">{errors[`weights.${k}`]}</div>}
            </div>
          ))}
        </div>

        <div className="p-4 border rounded">
          <h3 className="font-semibold mb-2">Source weights</h3>
          {Object.entries(settings.source_weights).map(([k,v]) => (
            <div key={k} className="flex flex-col mb-2">
              <div className="flex items-center gap-2">
                <label className="w-36 text-sm">{k}</label>
                <input type="number" step="0.01" value={v} onChange={e => setNested(`source_weights.${k}`, Number(e.target.value))} className="px-2 py-1 border rounded w-full" />
              </div>
              {errors[`source_weights.${k}`] && <div className="text-xs text-red-600 mt-1">{errors[`source_weights.${k}`]}</div>}
            </div>
          ))}
        </div>

        <div className="p-4 border rounded">
          <h3 className="font-semibold mb-2">Event priors</h3>
          {Object.entries(settings.event_priors).map(([k,v]) => (
            <div key={k} className="flex flex-col mb-2">
              <div className="flex items-center gap-2">
                <label className="w-36 text-sm">{k}</label>
                <input type="number" step="0.01" value={v} onChange={e => setNested(`event_priors.${k}`, Number(e.target.value))} className="px-2 py-1 border rounded w-full" />
              </div>
              {errors[`event_priors.${k}`] && <div className="text-xs text-red-600 mt-1">{errors[`event_priors.${k}`]}</div>}
            </div>
          ))}
        </div>
      </div>

      <div className="mt-4 flex gap-2 items-center">
        <button onClick={onSave} disabled={saving || Object.keys(errors).length>0} className={`px-4 py-2 ${saving || Object.keys(errors).length>0 ? 'bg-slate-300 text-slate-600' : 'bg-sky-600 text-white'} rounded`}>{saving ? 'Saving...' : 'Save'}</button>
        <button onClick={() => { setMsg(null); window.location.reload() }} className="px-4 py-2 border rounded">Reload</button>
        {Object.keys(errors).length > 0 && <div className="text-sm text-red-600">Please fix validation errors before saving ({Object.keys(errors).length})</div>}
      </div>
    </div>
  )
}
