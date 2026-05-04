import { useEffect, useState } from 'react'
import { apiFetch } from '../lib/api'

type IndicatorsResp = { rows: Record<string, unknown>[]; total: number }

export function AdjustmentsPage() {
  const [busy, setBusy] = useState(false)
  const [log, setLog] = useState<string[]>([])
  const [preview, setPreview] = useState<IndicatorsResp | null>(null)

  const push = (m: string) => setLog((l) => [...l, m])

  async function refreshPreview() {
    try {
      const r = await apiFetch<IndicatorsResp>('/api/v1/econ/indicators?limit=20')
      setPreview(r)
    } catch {
      setPreview(null)
    }
  }

  useEffect(() => {
    refreshPreview().catch(() => {})
  }, [])

  async function fetchMacro() {
    setBusy(true)
    push('Fetching macro indicators…')
    try {
      await apiFetch('/api/v1/pipeline/econ/fetch', { method: 'POST' })
      push('Fetch complete.')
      await refreshPreview()
    } catch (e) {
      push(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  async function applyReal() {
    setBusy(true)
    push('Applying real-value tables…')
    try {
      await apiFetch('/api/v1/pipeline/econ/apply', { method: 'POST' })
      push('Apply complete.')
    } catch (e) {
      push(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <h1 className="section-title">Adjustments</h1>
      <p className="section-subtitle">
        Refresh macro series (HCP / FRED / World Bank / BAM per <code className="text-emerald-400/80">econ_settings</code>),
        then rebuild <code className="text-emerald-400/80">*_real</code> tables.
      </p>

      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          disabled={busy}
          onClick={fetchMacro}
          className="btn-secondary"
        >
          Fetch indicators
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={applyReal}
          className="btn-primary"
        >
          Apply real values
        </button>
      </div>

      <div className="app-card p-4">
        <h2 className="mb-2 text-sm font-medium text-slate-300">Recent econ_indicators</h2>
        {preview && preview.rows.length ? (
          <div className="overflow-x-auto text-xs">
            <table className="w-full border-collapse">
              <thead>
                <tr className="text-left text-slate-500">
                  {Object.keys(preview.rows[0]).map((k) => (
                    <th key={k} className="border-b border-slate-800 px-2 py-1">
                      {k}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {preview.rows.map((r, i) => (
                  <tr key={i} className="border-b border-slate-800/60">
                    {Object.values(r).map((v, j) => (
                      <td key={j} className="px-2 py-1 text-slate-300">
                        {String(v)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-xs text-slate-500">No rows (run fetch first).</p>
        )}
      </div>

      <div className="app-card bg-black/45 p-4 font-mono text-xs text-slate-400">
        {log.map((l, i) => (
          <div key={i}>{l}</div>
        ))}
      </div>
    </div>
  )
}
