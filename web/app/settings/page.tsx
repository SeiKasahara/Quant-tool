import React from 'react'
import dynamic from 'next/dynamic'

const Editor = dynamic(() => import('./components/Editor'), { ssr: false })

export default function Page() {
  return (
    <div className="container mx-auto p-6">
      <h1 className="text-2xl font-bold mb-4">Fuser Settings</h1>
      <p className="text-sm text-slate-600 mb-4">Edit weights, source weights and event priors used to compute signal confidence.</p>
      <Editor />
    </div>
  )
}
