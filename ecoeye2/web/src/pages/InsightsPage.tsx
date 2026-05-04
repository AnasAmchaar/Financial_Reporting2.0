import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../lib/api'

type ReportingSummary = {
  table: string
  period_min: string | null
  period_max: string | null
  sum_nominal: number
  sum_real: number | null
  inflation_impact: number | null
  inflation_impact_note: string | null
  note: string | null
}

type EconStatus = {
  fred_api_key_set: boolean
  indicators: Record<string, { source: string | null; fetched_at: string | null }>
  econ_indicators_last_fetched_at: string | null
  note?: string
}

function fmt(n: number) {
  return n.toLocaleString(undefined, { maximumFractionDigits: 0 })
}

export function InsightsPage() {
  const [table] = useState('data_reel')
  const [summary, setSummary] = useState<ReportingSummary | null>(null)
  const [econ, setEcon] = useState<EconStatus | null>(null)
  const [err, setErr] = useState('')

  useEffect(() => {
    let cancelled = false
    setErr('')
    const q = new URLSearchParams({ table })
    Promise.all([
      apiFetch<ReportingSummary>(`/api/v1/reporting/summary?${q}`).catch((e) => {
        throw e
      }),
      fetch(`${import.meta.env.VITE_API_BASE ?? ''}/api/v1/econ/status`, {
        headers: { Accept: 'application/json' },
      }).then((r) => (r.ok ? r.json() : Promise.reject(new Error(r.statusText)))),
    ])
      .then(([s, e]) => {
        if (!cancelled) {
          setSummary(s as ReportingSummary)
          setEcon(e as EconStatus)
        }
      })
      .catch((e) => {
        if (!cancelled) setErr(e instanceof Error ? e.message : String(e))
      })
    return () => {
      cancelled = true
    }
  }, [table])

  return (
    <div className="mx-auto max-w-5xl space-y-8">
      <div>
        <h1 className="section-title">Insights</h1>
        <p className="section-subtitle mt-2 max-w-3xl">
          Reporting-first view of your dataset: period coverage, nominal vs real totals, and macro
          ingestion status. Open <strong className="text-slate-300">Visualize</strong> for trends
          and comparisons.
        </p>
      </div>

      {err ? (
        <div className="app-card border-amber-500/40 bg-amber-950/40 p-4 text-sm text-amber-200">
          <p className="font-medium">Could not load reporting data</p>
          <p className="mt-1 text-amber-200/80">{err}</p>
          <p className="mt-2 text-xs text-amber-200/60">
            Run ETL from <Link className="text-emerald-400 underline" to="/ingest">Ingest</Link>, then
            macro fetch + apply from{' '}
            <Link className="text-emerald-400 underline" to="/adjustments">Adjustments</Link> if you need
            real columns.
          </p>
        </div>
      ) : null}

      {summary ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="app-card p-4">
            <div className="text-xs font-medium uppercase tracking-wide text-slate-500">Period</div>
            <div className="mt-1 text-lg font-semibold text-white">
              {summary.period_min && summary.period_max
                ? `${summary.period_min.slice(0, 10)} → ${summary.period_max.slice(0, 10)}`
                : '—'}
            </div>
            <div className="mt-1 text-xs text-slate-500">{summary.table}</div>
          </div>
          <div className="app-card p-4">
            <div className="text-xs font-medium uppercase tracking-wide text-slate-500">Sum nominal</div>
            <div className="mt-1 text-lg font-semibold text-emerald-300">{fmt(summary.sum_nominal)}</div>
          </div>
          <div className="app-card p-4">
            <div className="text-xs font-medium uppercase tracking-wide text-slate-500">Sum real</div>
            <div className="mt-1 text-lg font-semibold text-sky-300">
              {summary.sum_real != null ? fmt(summary.sum_real) : '—'}
            </div>
            {summary.note ? <div className="mt-2 text-xs text-slate-500">{summary.note}</div> : null}
          </div>
          <div className="app-card p-4">
            <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Nominal − real
            </div>
            <div className="mt-1 text-lg font-semibold text-slate-100">
              {summary.inflation_impact != null ? fmt(summary.inflation_impact) : '—'}
            </div>
            {summary.inflation_impact_note ? (
              <div className="mt-2 text-xs text-slate-500">{summary.inflation_impact_note}</div>
            ) : null}
          </div>
        </div>
      ) : !err ? (
        <div className="text-sm text-slate-500">Loading…</div>
      ) : null}

      <div className="app-card p-5">
        <h2 className="text-sm font-semibold text-slate-200">Macro ingestion</h2>
        {econ ? (
          <ul className="mt-3 space-y-2 text-sm text-slate-300">
            <li>
              <span className="text-slate-500">FRED API key:</span>{' '}
              {econ.fred_api_key_set ? (
                <span className="text-emerald-400">set</span>
              ) : (
                <span className="text-amber-400">not set</span>
              )}
            </li>
            <li>
              <span className="text-slate-500">Last econ fetch:</span>{' '}
              {econ.econ_indicators_last_fetched_at ?? '—'}
            </li>
            {['cpi', 'ppi', 'cpi_yoy'].map((k) => {
              const row = econ.indicators[k]
              if (!row) return null
              return (
                <li key={k}>
                  <span className="text-slate-500">{k}:</span> {row.source ?? '—'}{' '}
                  <span className="text-slate-600">({row.fetched_at ?? '—'})</span>
                </li>
              )
            })}
            {econ.note ? <li className="text-xs text-slate-500">{econ.note}</li> : null}
          </ul>
        ) : (
          <p className="mt-2 text-xs text-slate-500">Loading status…</p>
        )}
      </div>

      <div className="flex flex-wrap gap-3">
        <Link to="/visualize" className="btn-primary inline-block text-center">
          Open Visualize
        </Link>
        <Link to="/ingest" className="btn-secondary inline-block text-center">
          Ingest data
        </Link>
      </div>
    </div>
  )
}
