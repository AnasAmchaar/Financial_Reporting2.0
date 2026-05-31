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

type EvaDemo = {
  demo: string
  points: {
    period: string
    nopat: number
    invested_capital: number
    wacc: number
    capital_charge: number
    eva: number
  }[]
}

type VpmfDemo = {
  demo: string
  points: {
    period: string
    nominal: number
    price_effect: number
    volume_effect: number
    delta: number
    delta_price: number
    delta_volume: number
  }[]
}

type EconStatus = {
  fred_api_key_set: boolean
  indicators: Record<string, { source: string | null; fetched_at: string | null; status: 'good' | 'bad' }>
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
  const [eva, setEva] = useState<EvaDemo | null>(null)
  const [vpmf, setVpmf] = useState<VpmfDemo | null>(null)
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
      apiFetch<EvaDemo>(`/api/v1/reporting/eva-demo`).catch(() => null),
      apiFetch<VpmfDemo>(`/api/v1/reporting/vpmf-demo?${q}`).catch(() => null),
    ])
      .then(([s, e, ev, vp]) => {
        if (!cancelled) {
          setSummary(s as ReportingSummary)
          setEcon(e as EconStatus)
          if (ev) setEva(ev as EvaDemo)
          if (vp) setVpmf(vp as VpmfDemo)
        }
      })
      .catch((e) => {
        if (!cancelled) setErr(e instanceof Error ? e.message : String(e))
      })
    return () => {
      cancelled = true
    }
  }, [table])

  useEffect(() => {
    // Expose current page context for the AI ChatBot
    window.__ECOEYE_CONTEXT__ = {
      page: 'Insights',
      summary: summary,
      econ_indicators: econ,
      eva_metrics: eva,
      vpmf_metrics: vpmf
    }
  }, [summary, econ, eva, vpmf])

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

      {/* Advanced Economic Demo Section */}
      {(eva || vpmf) && (
        <div className="mt-8 space-y-6">
          <h2 className="text-xl font-semibold text-white border-b border-slate-800 pb-2">Advanced Economics Demo</h2>
          
          <div className="grid gap-4 sm:grid-cols-2">
            {/* EVA Card */}
            {eva && eva.points.length > 0 && (() => {
              const totalNopat = eva.points.reduce((sum, p) => sum + p.nopat, 0)
              const totalEva = eva.points.reduce((sum, p) => sum + p.eva, 0)
              const waccPct = (eva.points[0].wacc * 100).toFixed(1)
              return (
                <div 
                  className="app-card p-5 border-indigo-500/30 bg-indigo-950/20" 
                  style={{ boxShadow: '0 10px 40px -20px rgba(99,102,241,0.2)' }}
                >
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-sm font-semibold text-indigo-300 uppercase tracking-wider">Economic Value Added (EVA)</h3>
                    <span className="badge-muted">WACC: {waccPct}%</span>
                  </div>
                  <div className="grid grid-cols-2 gap-4 mt-4">
                    <div>
                      <div className="text-xs text-slate-500">Nominal Profit (NOPAT proxy)</div>
                      <div className="mt-1 text-xl font-medium text-slate-200">{fmt(totalNopat)}</div>
                    </div>
                    <div>
                      <div className="text-xs text-slate-500">True Economic Profit (EVA)</div>
                      <div className={`mt-1 text-xl font-bold ${totalEva >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                        {totalEva > 0 ? '+' : ''}{fmt(totalEva)}
                      </div>
                    </div>
                  </div>
                  <p className="mt-3 text-xs text-indigo-300/70 border-t border-indigo-500/20 pt-3">
                    Evaluates if the generated profit covers the cost of capital. A negative EVA indicates wealth destruction despite nominal profits.
                  </p>
                </div>
              )
            })()}

            {/* VPMF Card */}
            {vpmf && vpmf.points.length > 0 && (() => {
              const lastPoint = vpmf.points[vpmf.points.length - 1]
              return (
                <div 
                  className="app-card p-5 border-fuchsia-500/30 bg-fuchsia-950/20"
                  style={{ boxShadow: '0 10px 40px -20px rgba(217,70,239,0.2)' }}
                >
                  <h3 className="text-sm font-semibold text-fuchsia-300 uppercase tracking-wider mb-2">Growth Decomposition (VPMF)</h3>
                  <div className="text-xs text-slate-400 mb-4">Latest Period: {lastPoint.period}</div>
                  
                  <div className="space-y-3">
                    <div>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-slate-400">Total Nominal Amount</span>
                        <span className="font-mono text-slate-200">{fmt(lastPoint.nominal)}</span>
                      </div>
                    </div>
                    <div className="pl-4 border-l-2 border-slate-700 space-y-2">
                      <div>
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-fuchsia-400">Price / Inflation Effect</span>
                          <span className="font-mono text-fuchsia-300">{fmt(lastPoint.price_effect)}</span>
                        </div>
                        <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                          <div className="h-full bg-fuchsia-500" style={{ width: `${Math.max(0, Math.min(100, (lastPoint.price_effect / lastPoint.nominal) * 100))}%` }} />
                        </div>
                      </div>
                      <div>
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-sky-400">Real Volume Growth</span>
                          <span className="font-mono text-sky-300">{fmt(lastPoint.volume_effect)}</span>
                        </div>
                        <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                          <div className="h-full bg-sky-500" style={{ width: `${Math.max(0, Math.min(100, (lastPoint.volume_effect / lastPoint.nominal) * 100))}%` }} />
                        </div>
                      </div>
                    </div>
                  </div>
                  <p className="mt-4 text-xs text-fuchsia-300/70 border-t border-fuchsia-500/20 pt-3">
                    Isolates how much of the amount is driven by price inflation versus actual volume/mix growth.
                  </p>
                </div>
              )
            })()}
          </div>
        </div>
      )}

      <div className="app-card p-5">
        <h2 className="text-sm font-semibold text-slate-200">Macro ingestion</h2>
        {econ ? (
          <ul className="mt-3 space-y-3 text-sm text-slate-300">
            <li className="flex justify-between items-center border-b border-slate-800 pb-2">
              <span className="text-slate-500">FRED API key:</span>{' '}
              {econ.fred_api_key_set ? (
                <span className="text-emerald-400 px-2 py-0.5 bg-emerald-400/10 rounded-full text-xs">set</span>
              ) : (
                <span className="text-amber-400 px-2 py-0.5 bg-amber-400/10 rounded-full text-xs">not set</span>
              )}
            </li>
            <li className="flex justify-between items-center border-b border-slate-800 pb-2">
              <span className="text-slate-500">Last econ fetch:</span>{' '}
              <span className="text-slate-300">{econ.econ_indicators_last_fetched_at ?? '—'}</span>
            </li>
            <li className="pt-2">
              <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Indicator Status</div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                {Object.entries(econ.indicators).map(([k, row]) => (
                  <div key={k} className="bg-slate-900/50 rounded-lg p-3 border border-slate-800/50 relative overflow-hidden">
                    <div className="flex items-center space-x-2 mb-1">
                      {row.status === 'good' ? (
                        <div className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)]" />
                      ) : (
                        <div className="w-2 h-2 rounded-full bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.8)]" />
                      )}
                      <span className="font-medium text-slate-200 capitalize">{k}</span>
                    </div>
                    <div className="text-xs text-slate-500 mt-2">
                      <div className="flex justify-between"><span>Source:</span> <span className="text-slate-400">{row.source ?? '—'}</span></div>
                      <div className="flex justify-between mt-1"><span>Latest:</span> <span className="text-slate-400">{row.fetched_at ? row.fetched_at.slice(0, 10) : '—'}</span></div>
                    </div>
                  </div>
                ))}
              </div>
            </li>
            {econ.note ? <li className="text-xs text-amber-500/80 mt-4">{econ.note}</li> : null}
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
