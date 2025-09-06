"use client"
import { useEffect, useState } from 'react'
import { getSources, createSource, testSource, runSource } from '@/lib/api'

export default function SourcesPage() {
  const [sources, setSources] = useState<any[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [name, setName] = useState('')

  const load = async () => {
    setLoading(true)
    try {
      const res = await getSources()
      setSources(res)
    } catch (e) {
      setSources([])
    } finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const handleCreate = async () => {
    const payload = { name: name || 'New RSS', type: 'news', params: { rss: '' }, enabled: false }
    const res = await createSource(payload)
    setName('')
    load()
  }

  const handleTest = async (id: number) => {
    await testSource(id)
    alert('Test triggered (check backend logs or preview)')
  }

  const handleRun = async (id: number) => {
    await runSource(id)
    alert('Run requested')
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Sources</h2>
        <div className="flex items-center space-x-2">
          <input className="border px-2 py-1 rounded" value={name} onChange={e => setName(e.target.value)} placeholder="Source name" />
          <button onClick={handleCreate} className="px-3 py-1 bg-blue-600 text-white rounded">Create</button>
        </div>
      </div>

      {loading && <div>Loading...</div>}

      {!loading && sources && (
        <div className="space-y-2">
          {sources.map(s => (
            <div key={s.id} className="p-4 bg-card rounded flex justify-between items-center">
              <div>
                <div className="font-semibold">{s.name}</div>
                <div className="text-sm text-muted-foreground">{s.type} • {s.enabled ? 'Enabled' : 'Disabled'}</div>
              </div>
              <div className="space-x-2">
                <button onClick={() => handleTest(s.id)} className="px-3 py-1 bg-yellow-400 rounded">Test</button>
                <button onClick={() => handleRun(s.id)} className="px-3 py-1 bg-green-600 text-white rounded">Run</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
