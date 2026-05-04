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
}

type Preview = {
  base_period: string
  discount: Record<string, unknown>
  adjustment_tables: string[]
}

export function SettingsPage() {
  const [h, setH] = useState<Health | null>(null)
  const [p, setP] = useState<Preview | null>(null)
  const [err, setErr] = useState('')

  useEffect(() => {
    apiFetch<Health>('/api/v1/health')
      .then(setH)
      .catch((e) => setErr(String(e.message)))
    apiFetch<Preview>('/api/v1/econ/settings-preview')
      .then(setP)
      .catch(() => {})
  }, [])

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <h1 className="section-title">Settings</h1>
      {err ? <p className="text-sm text-red-400">{err}</p> : null}

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
