"use client"
import { useState } from 'react'
import { importUrl } from '@/lib/api'

export default function ImportPage() {
  const [url, setUrl] = useState('')
  const [preview, setPreview] = useState<any | null>(null)
  const [loading, setLoading] = useState(false)

  const handlePreview = async () => {
    setLoading(true)
    try {
      const res = await importUrl(url, true)
      setPreview(res)
    } catch (e) {
      setPreview({ error: String(e) })
    } finally { setLoading(false) }
  }

  const handleImport = async () => {
    setLoading(true)
    try {
      const res = await importUrl(url, false)
      alert('Import requested')
    } catch (e) {
      alert('Import failed: ' + String(e))
    } finally { setLoading(false) }
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Import URL</h2>
      <div className="flex space-x-2">
        <input className="flex-1 border px-2 py-1 rounded" value={url} onChange={e => setUrl(e.target.value)} placeholder="https://..." />
        <button onClick={handlePreview} className="px-3 py-1 bg-yellow-400 rounded">Preview</button>
        <button onClick={handleImport} className="px-3 py-1 bg-green-600 text-white rounded">Import</button>
      </div>

      <div className="bg-card rounded p-4">
        <h3 className="font-semibold mb-2">Preview</h3>
        {loading && <div>Loading...</div>}
        {!loading && preview && (
          <div>
            {preview.error && <div className="text-red-600">{preview.error}</div>}
            {preview.title && <h4 className="font-semibold">{preview.title}</h4>}
            {preview.published && <div className="text-sm text-muted-foreground">{preview.published}</div>}
            {preview.excerpt && <p className="mt-2">{preview.excerpt}</p>}
          </div>
        )}
        {!loading && !preview && <div className="text-sm text-muted-foreground">No preview yet</div>}
      </div>
    </div>
  )
}
