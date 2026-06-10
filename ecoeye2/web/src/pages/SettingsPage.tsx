import { useEffect, useState } from 'react'
import { apiFetch } from '../lib/api'

type Health = {
  app: string
  status: string
  db_path: string
  raw_dir: string
  project_root: string
  fred_api_key_set: boolean
  ecoeye2_api_key_set: boolean
  gemini_api_key_set: boolean
  groq_api_key_set: boolean
  ai_provider: string
}

type Preview = {
  base_period: string
  discount: Record<string, unknown>
  adjustment_tables: string[]
}

type ProviderInfo = {
  id: string
  label: string
  model: string
  api_key_set: boolean
}

type ProviderStatus = {
  active: string
  providers: ProviderInfo[]
}

export function SettingsPage() {
  const [h, setH] = useState<Health | null>(null)
  const [p, setP] = useState<Preview | null>(null)
  const [err, setErr] = useState('')
  const [providerStatus, setProviderStatus] = useState<ProviderStatus | null>(null)
  const [switching, setSwitching] = useState(false)
  const [providerMsg, setProviderMsg] = useState<{ type: 'ok' | 'err'; text: string } | null>(null)

  useEffect(() => {
    apiFetch<Health>('/api/v1/health')
      .then(setH)
      .catch((e) => setErr(String(e.message)))
    apiFetch<Preview>('/api/v1/econ/settings-preview')
      .then(setP)
      .catch(() => {})
    apiFetch<ProviderStatus>('/api/v1/ai/provider')
      .then(setProviderStatus)
      .catch(() => {})
  }, [])

  const switchProvider = async (id: string) => {
    if (switching || providerStatus?.active === id) return
    setSwitching(true)
    setProviderMsg(null)
    try {
      const result = await apiFetch<ProviderStatus>('/api/v1/ai/provider', {
        method: 'POST',
        body: JSON.stringify({ provider: id }),
      })
      setProviderStatus(result)
      setProviderMsg({ type: 'ok', text: `Switched to ${result.providers.find(p => p.id === result.active)?.label ?? result.active}` })
    } catch (e: any) {
      setProviderMsg({ type: 'err', text: e.message || 'Failed to switch provider' })
    } finally {
      setSwitching(false)
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <h1 className="section-title">Settings</h1>
      {err ? <p className="text-sm text-red-400">{err}</p> : null}

      {/* ── AI Provider Card ─────────────────────────────────────────── */}
      {providerStatus ? (
        <div className="app-card p-5 text-sm">
          <h2 className="mb-4 font-medium text-slate-200 flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-violet-400">
              <path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/>
            </svg>
            AI Provider
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {providerStatus.providers.map((prov) => {
              const isActive = providerStatus.active === prov.id
              return (
                <button
                  key={prov.id}
                  onClick={() => switchProvider(prov.id)}
                  disabled={switching}
                  className={`relative flex flex-col items-start gap-2 rounded-xl border p-4 text-left transition-all duration-200 ${
                    isActive
                      ? 'border-emerald-500/60 bg-emerald-500/10 shadow-[0_0_12px_rgba(16,185,129,0.15)]'
                      : 'border-slate-700/60 bg-slate-800/40 hover:border-slate-600 hover:bg-slate-800/70'
                  } ${switching ? 'opacity-60 cursor-wait' : 'cursor-pointer'}`}
                >
                  {/* Active indicator */}
                  {isActive && (
                    <span className="absolute top-3 right-3 flex h-2 w-2">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
                    </span>
                  )}

                  <span className={`font-semibold text-sm ${isActive ? 'text-emerald-300' : 'text-slate-300'}`}>
                    {prov.label}
                  </span>

                  <span className="text-[11px] text-slate-500 font-mono">
                    model: {prov.model}
                  </span>

                  <span className={`inline-flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full ${
                    prov.api_key_set
                      ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/25'
                      : 'bg-amber-500/15 text-amber-400 border border-amber-500/25'
                  }`}>
                    <span className={`inline-block w-1.5 h-1.5 rounded-full ${prov.api_key_set ? 'bg-emerald-400' : 'bg-amber-400'}`} />
                    {prov.api_key_set ? 'API Key Set' : 'Key Missing'}
                  </span>
                </button>
              )
            })}
          </div>

          {providerMsg && (
            <p className={`mt-3 text-xs ${providerMsg.type === 'ok' ? 'text-emerald-400' : 'text-red-400'}`}>
              {providerMsg.type === 'ok' ? '✓' : '✗'} {providerMsg.text}
            </p>
          )}

          <p className="mt-3 text-[11px] text-slate-500">
            Embeddings always use Google GenAI regardless of the selected LLM provider.
          </p>
        </div>
      ) : null}

      {/* ── Runtime Card ─────────────────────────────────────────────── */}
      {h ? (
        <div className="app-card p-5 text-sm">
          <h2 className="mb-3 font-medium text-slate-200">Runtime</h2>
          <dl className="space-y-2 text-slate-400">
            <div>
              <dt className="text-xs uppercase text-slate-500">Database</dt>
              <dd className="break-all font-mono text-xs text-emerald-400/90">{h.db_path}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase text-slate-500">Raw uploads</dt>
              <dd className="break-all font-mono text-xs">{h.raw_dir}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase text-slate-500">FRED_API_KEY</dt>
              <dd>{h.fred_api_key_set ? 'set' : 'not set (monthly CPI fallback limited)'}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase text-slate-500">ECOEYE2_API_KEY</dt>
              <dd>{h.ecoeye2_api_key_set ? 'set (API requires X-Api-Key)' : 'not set (open API)'}</dd>
            </div>
          </dl>
        </div>
      ) : null}

      {/* ── Economic Layer Card ───────────────────────────────────────── */}
      {p ? (
        <div className="app-card p-5 text-sm">
          <h2 className="mb-3 font-medium text-slate-200">Economic layer (read-only)</h2>
          <p className="mb-2 text-slate-400">
            Base period: <code className="text-emerald-400">{p.base_period}</code>
          </p>
          <p className="text-xs text-slate-500">Adjusted tables: {p.adjustment_tables.join(', ')}</p>
        </div>
      ) : null}

      <p className="text-xs text-slate-500">
        API docs: <a className="text-emerald-400 hover:underline" href="/docs">/docs</a> (when backend is running on
        same origin in production, or port 8000 in dev).
      </p>
    </div>
  )
}
