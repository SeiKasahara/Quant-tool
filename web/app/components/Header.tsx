"use client"
import React, { useEffect, useState } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'

export default function Header() {
  const pathname = usePathname()
  const router = useRouter()
  const [open, setOpen] = useState(false)
  const [userMenu, setUserMenu] = useState(false)
  const [username, setUsername] = useState<string | null>(null)
  const [avatar, setAvatar] = useState<string | null>(null)
  const [role, setRole] = useState<string | null>(null)
  const [showLogin, setShowLogin] = useState(false)
  const [isRegister, setIsRegister] = useState(false)
  const [loginUser, setLoginUser] = useState('')
  const [loginPass, setLoginPass] = useState('')
  const [loginEmail, setLoginEmail] = useState('')
  const [loginLoading, setLoginLoading] = useState(false)
  const [loginError, setLoginError] = useState<string | null>(null)
  const [q, setQ] = useState('')

  const links = [
    { href: '/signals', label: 'Signals' },
    { href: '/documents', label: 'Documents' },
    { href: '/event-patterns', label: 'Event Patterns' },
    { href: '/sources', label: 'Sources' },
    { href: '/ingest', label: 'Ingest' },
    { href: '/import', label: 'Import' }
  ]

  function isActive(href: string) {
    if (href === '/') return pathname === '/'
    return pathname?.startsWith(href)
  }

      useEffect(() => {
    let mounted = true
    ;(async () => {
      try {
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE || ''}/auth/me`)
        if (!res.ok) return
        const body = await res.json()
        if (mounted) {
          if (body?.username) setUsername(body.username)
          if (body?.avatar) setAvatar(body.avatar)
          if (body?.role) setRole(body.role)
        }
      } catch (_) {
        // ignore
      }
    })()
    return () => { mounted = false }
  }, [])

  function onSearch(e: React.FormEvent) {
    e.preventDefault()
    // navigate to signals with query param
    router.push(`/signals?q=${encodeURIComponent(q)}`)
  }

  async function onLogout() {
    try {
      await fetch(`${process.env.NEXT_PUBLIC_API_BASE || ''}/auth/logout`, { method: 'POST' })
    } catch (_) {
      // ignore
    }
    setUsername(null)
    router.push('/')
  }

  return (
    <header className="border-b bg-white">
      <div className="container mx-auto px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button className="md:hidden p-2" onClick={() => setOpen(!open)} aria-label="Toggle menu">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16"/></svg>
          </button>
          <Link href="/" className="text-xl font-bold">Signal Detection</Link>
          <nav className={`hidden md:flex items-center space-x-2 text-sm`}> 
            {links.map(l => (
              <Link key={l.href} href={l.href} className={`px-3 py-2 rounded transition focus:outline-none focus:ring-2 focus:ring-sky-200 ${isActive(l.href) ? 'bg-sky-100 text-sky-700 shadow-sm' : 'hover:bg-slate-100'}`}>
                {l.label}
              </Link>
            ))}
          </nav>
        </div>

        <div className="flex items-center gap-3">
          <Link href="/event-patterns" className="hidden sm:inline-flex items-center p-2 rounded hover:bg-slate-100" aria-label="Event patterns">
            <img src="/setting.svg" alt="Settings" />
          </Link>
          <form onSubmit={onSearch} className="hidden sm:flex items-center gap-2">
            <input value={q} onChange={e => setQ(e.target.value)} placeholder="Search signals or tickers" className="px-3 py-1 border rounded w-60" />
            <button type="submit" className="px-3 py-1 bg-sky-600 text-white rounded">Search</button>
          </form>

          {/* Login button (dev) */}
          {!username && (
            <button onClick={() => setShowLogin(true)} className="px-3 py-1 border rounded mr-2">Login</button>
          )}

          <div className="relative">
            <div className="flex items-center gap-2">
              {avatar ? (
                <img src={avatar} alt="avatar" className="w-6 h-6 rounded-full" />
              ) : (
                <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path strokeWidth="1.5" d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zM6 20c0-3.314 2.686-6 6-6s6 2.686 6 6"/></svg>
              )}
              <button onClick={() => setUserMenu(!userMenu)} className="px-2 py-1 flex items-center gap-2">
                <span>{username || 'User'}</span>
                {role && <span className="text-xs text-slate-500 rounded px-1 py-0.5 bg-slate-100">{role}</span>}
              </button>
            </div>
            {userMenu && (
              <div className="absolute right-0 mt-2 w-48 bg-white border rounded shadow z-20">
                <Link href="/profile" className="block px-3 py-2 hover:bg-slate-50">Profile</Link>
                <button onClick={onLogout} className="w-full text-left px-3 py-2 hover:bg-slate-50">Logout</button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Login modal */}
          {showLogin && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded shadow-lg w-full max-w-md p-6">
            <h3 className="text-lg font-semibold mb-4">{isRegister ? 'Create account' : 'Sign in'}</h3>
            {loginError && <div className="text-sm text-red-600 mb-2">{loginError}</div>}
            <form onSubmit={async (e) => {
              e.preventDefault()
              setLoginError(null)
              setLoginLoading(true)
              try {
                let emailToken = null
                if (isRegister){
                  const reg = await fetch(`${process.env.NEXT_PUBLIC_API_BASE || ''}/auth/register`, {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username: loginUser, password: loginPass, email: loginEmail })
                  })
                  if (!reg.ok){ const t = await reg.text(); throw new Error(t || 'Register failed') }
                  const rb = await reg.json()
                  emailToken = rb?.email_token
                }

                const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE || ''}/auth/login`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ username: loginUser, password: loginPass })
                })
                if (!res.ok) {
                  const txt = await res.text()
                  throw new Error(txt || 'Login failed')
                }
                const body = await res.json()
                if (body?.user) {
                  setUsername(body.user.username)
                  setAvatar(body.user.avatar)
                  setRole(body.user.role)
                }
                setShowLogin(false)
                setLoginUser('')
                setLoginPass('')
                setLoginEmail('')
                if (emailToken){
                  // show token to user in dev mode
                  alert('Email confirmation token (dev): ' + emailToken)
                }
              } catch (err: any) {
                setLoginError(String(err?.message || err))
              } finally {
                setLoginLoading(false)
              }
            }}>
              <label className="block mb-2 text-sm">Username</label>
              <input value={loginUser} onChange={e => setLoginUser(e.target.value)} className="w-full mb-3 px-3 py-2 border rounded" />
              <label className="block mb-2 text-sm">Password</label>
              <input type="password" value={loginPass} onChange={e => setLoginPass(e.target.value)} className="w-full mb-4 px-3 py-2 border rounded" />
              <div className="flex items-center justify-end gap-2">
                <button type="button" onClick={() => setShowLogin(false)} className="px-3 py-1">Cancel</button>
                <button type="submit" disabled={loginLoading} className="px-3 py-1 bg-sky-600 text-white rounded">{loginLoading ? '...' : 'Sign in'}</button>
              </div>
            </form>
            <div className="flex items-center justify-between mt-3">
              <div className="text-xs text-slate-500">{isRegister ? 'After registration you will be logged in.' : 'New? Create an account.'}</div>
              <button onClick={() => setIsRegister(!isRegister)} className="text-sm text-sky-600">{isRegister ? 'Switch to login' : 'Register'}</button>
            </div>
          </div>
        </div>
      )}

      {/* Mobile menu */}
      {open && (
        <div className="md:hidden border-t bg-white">
          <div className="px-4 py-3 space-y-2">
            {links.map(l => (
              <Link key={l.href} href={l.href} className={`block px-3 py-2 rounded ${isActive(l.href) ? 'bg-sky-100 text-sky-700' : 'hover:bg-slate-100'}`}>{l.label}</Link>
            ))}
            <form onSubmit={onSearch} className="flex items-center gap-2 mt-2">
              <input value={q} onChange={e => setQ(e.target.value)} placeholder="Search" className="flex-1 px-3 py-1 border rounded" />
              <button type="submit" className="px-3 py-1 bg-sky-600 text-white rounded">Go</button>
            </form>
          </div>
        </div>
      )}
    </header>
  )
}
