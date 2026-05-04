import { useEffect, useMemo, useState } from 'react'
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { apiFetch } from '../lib/api'

type SeriesResp = {
  table: string
  mode: string
  group_by: string
  points: { period: string; nominal: number | null; real: number | null }[]
}

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

function toCsv(rows: SeriesResp['points'], mode: string) {
  const header =
    mode === 'both'
      ? 'period,nominal,real,delta_pct'
      : mode === 'real'
        ? 'period,real'
        : 'period,nominal'
  const lines = [header]
  for (const p of rows) {
    const d =
      p.nominal != null && p.nominal !== 0 && p.real != null
        ? ((p.real / p.nominal - 1) * 100).toFixed(4)
        : ''
    if (mode === 'both') lines.push(`${p.period},${p.nominal ?? ''},${p.real ?? ''},${d}`)
    else if (mode === 'real') lines.push(`${p.period},${p.real ?? ''}`)
    else lines.push(`${p.period},${p.nominal ?? ''}`)
  }
  return lines.join('\n')
}

function fmt(n: number) {
  return n.toLocaleString(undefined, { maximumFractionDigits: 0 })
}

export function VisualizePage() {
  const [table, setTable] = useState('data_reel')
  const [mode, setMode] = useState<'nominal' | 'real' | 'both'>('both')
  const [groupBy, setGroupBy] = useState<'month' | 'partner' | 'channel'>('month')
  const [chartKind, setChartKind] = useState<'line' | 'grouped'>('line')
  const [data, setData] = useState<SeriesResp['points']>([])
  const [summary, setSummary] = useState<ReportingSummary | null>(null)
  const [err, setErr] = useState('')

  useEffect(() => {
    const q = new URLSearchParams({ table, mode, group_by: groupBy })
    apiFetch<SeriesResp>(`/api/v1/analytics/series?${q}`)
      .then((r) => {
        setData(r.points)
        setErr('')
      })
      .catch((e) => setErr(e instanceof Error ? e.message : String(e)))
  }, [table, mode, groupBy])

  useEffect(() => {
    const q = new URLSearchParams({ table })
    apiFetch<ReportingSummary>(`/api/v1/reporting/summary?${q}`)
      .then(setSummary)
      .catch(() => setSummary(null))
  }, [table])

  const chartData = useMemo(
    () =>
      data.map((p) => {
        const nominal = p.nominal ?? undefined
        const real = p.real ?? undefined
        const deltaPct =
          p.nominal != null && p.nominal !== 0 && p.real != null
            ? (p.real / p.nominal - 1) * 100
            : undefined
        return { ...p, nominal, real, deltaPct }
      }),
    [data],
  )

  function downloadCsv() {
    const blob = new Blob([toCsv(data, mode)], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${table}_${mode}_${groupBy}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  const showKpis = mode === 'both' && summary
  const emptySeries = !err && data.length === 0

  return (
    <div className="space-y-6">
      <h1 className="section-title">Visualize</h1>
      <p className="section-subtitle">
        Compare <strong className="text-slate-200">before</strong> (nominal) and{' '}
        <strong className="text-slate-200">after</strong> (inflation-adjusted) using{' '}
        <code className="text-emerald-400/80">*_real</code> when available. Delta % is{' '}
        <code className="text-slate-300">(real / nominal − 1) × 100</code> per group when both values exist.
      </p>

      {showKpis ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="app-card p-3">
            <div className="text-[11px] font-medium uppercase tracking-wide text-slate-500">Period</div>
            <div className="mt-0.5 text-sm font-semibold text-white">
              {summary.period_min && summary.period_max
                ? `${summary.period_min.slice(0, 10)} → ${summary.period_max.slice(0, 10)}`
                : '—'}
            </div>
          </div>
          <div className="app-card p-3">
            <div className="text-[11px] font-medium uppercase tracking-wide text-slate-500">Sum nominal</div>
            <div className="mt-0.5 text-sm font-semibold text-emerald-300">{fmt(summary.sum_nominal)}</div>
          </div>
          <div className="app-card p-3">
            <div className="text-[11px] font-medium uppercase tracking-wide text-slate-500">Sum real</div>
            <div className="mt-0.5 text-sm font-semibold text-sky-300">
              {summary.sum_real != null ? fmt(summary.sum_real) : '—'}
            </div>
            {summary.note ? <div className="mt-1 text-[11px] text-slate-500">{summary.note}</div> : null}
          </div>
          <div className="app-card p-3">
            <div className="text-[11px] font-medium uppercase tracking-wide text-slate-500">Nominal − real</div>
            <div className="mt-0.5 text-sm font-semibold text-slate-100">
              {summary.inflation_impact != null ? fmt(summary.inflation_impact) : '—'}
            </div>
          </div>
        </div>
      ) : null}

      <div className="app-card flex flex-wrap items-center gap-3 p-4">
        <div>
          <label className="mb-1 block text-xs text-slate-500">Dataset</label>
          <input value={table} onChange={(e) => setTable(e.target.value)} className="app-input" />
        </div>
        <div>
          <label className="mb-1 block text-xs text-slate-500">View</label>
          <select
            value={mode}
            onChange={(e) => setMode(e.target.value as typeof mode)}
            className="app-input"
          >
            <option value="nominal">Nominal (before)</option>
            <option value="real">Real (after)</option>
            <option value="both">Split (before / after)</option>
          </select>
        </div>
        <div>
          <label className="mb-1 block text-xs text-slate-500">Group by</label>
          <select
            value={groupBy}
            onChange={(e) => setGroupBy(e.target.value as typeof groupBy)}
            className="app-input"
          >
            <option value="month">Month</option>
            <option value="partner">Partner</option>
            <option value="channel">Channel</option>
          </select>
        </div>
        <div>
          <label className="mb-1 block text-xs text-slate-500">Chart</label>
          <select
            value={chartKind}
            onChange={(e) => setChartKind(e.target.value as 'line' | 'grouped')}
            className="app-input"
            disabled={mode !== 'both'}
            title={mode !== 'both' ? 'Grouped bars need nominal + real' : ''}
          >
            <option value="line">Lines</option>
            <option value="grouped">Grouped bars (nominal vs real)</option>
          </select>
        </div>
        <button type="button" onClick={downloadCsv} className="btn-secondary mt-5">
          Export CSV
        </button>
      </div>

      {err ? (
        <div className="app-card border-red-500/35 bg-red-950/30 p-4 text-sm text-red-200">
          <p className="font-medium">Chart request failed</p>
          <p className="mt-1 font-mono text-xs text-red-100/90">{err}</p>
          <ul className="mt-3 list-inside list-disc text-xs text-red-100/80">
            <li>
              If you see “No *_real with amount_real_*”, run <strong>Apply real values</strong> on the
              Adjustments page after macro fetch.
            </li>
            <li>Confirm the table name exists under Data and matches your ETL output.</li>
            <li>Run ETL from Ingest if tables are empty.</li>
          </ul>
        </div>
      ) : null}

      {emptySeries ? (
        <div className="app-card border-slate-700 p-4 text-sm text-slate-400">
          No series points returned for this table and grouping. Run ETL from Ingest, confirm{' '}
          <code className="text-emerald-400/90">{table}</code> has rows with <code className="text-slate-300">date</code>{' '}
          and <code className="text-slate-300">amount</code>.
        </div>
      ) : null}

      {!err && data.length > 0 ? (
        <div className="app-card h-[440px] w-full p-3">
          <ResponsiveContainer width="100%" height="100%">
            {mode === 'both' && chartKind === 'grouped' ? (
              <ComposedChart data={chartData} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis
                  dataKey="period"
                  tick={{ fill: '#94a3b8', fontSize: 10 }}
                  angle={-30}
                  textAnchor="end"
                  height={72}
                />
                <YAxis yAxisId="left" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <YAxis
                  yAxisId="right"
                  orientation="right"
                  tick={{ fill: '#cbd5e1', fontSize: 10 }}
                  tickFormatter={(v) => `${Number(v).toFixed(0)}%`}
                />
                <Tooltip
                  contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: 8 }}
                  labelStyle={{ color: '#e2e8f0' }}
                />
                <Legend />
                <Bar yAxisId="left" dataKey="nominal" name="Nominal" fill="#34d399" maxBarSize={28} />
                <Bar yAxisId="left" dataKey="real" name="Real" fill="#38bdf8" maxBarSize={28} />
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="deltaPct"
                  name="Delta %"
                  stroke="#fbbf24"
                  strokeWidth={2}
                  dot={false}
                />
              </ComposedChart>
            ) : mode === 'both' ? (
              <ComposedChart data={chartData} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis
                  dataKey="period"
                  tick={{ fill: '#94a3b8', fontSize: 11 }}
                  angle={-35}
                  textAnchor="end"
                  height={70}
                />
                <YAxis yAxisId="left" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <YAxis
                  yAxisId="right"
                  orientation="right"
                  tick={{ fill: '#cbd5e1', fontSize: 10 }}
                  tickFormatter={(v) => `${Number(v).toFixed(0)}%`}
                />
                <Tooltip
                  contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: 8 }}
                  labelStyle={{ color: '#e2e8f0' }}
                />
                <Legend />
                <Line
                  yAxisId="left"
                  type="monotone"
                  dataKey="nominal"
                  name="Nominal"
                  stroke="#34d399"
                  strokeWidth={2}
                  dot={false}
                />
                <Line yAxisId="left" type="monotone" dataKey="real" name="Real" stroke="#38bdf8" strokeWidth={2} dot={false} />
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="deltaPct"
                  name="Delta %"
                  stroke="#fbbf24"
                  strokeWidth={1.5}
                  dot={false}
                />
              </ComposedChart>
            ) : (
              <LineChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis
                  dataKey="period"
                  tick={{ fill: '#94a3b8', fontSize: 11 }}
                  angle={-35}
                  textAnchor="end"
                  height={70}
                />
                <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <Tooltip
                  contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: 8 }}
                  labelStyle={{ color: '#e2e8f0' }}
                />
                <Legend />
                {mode === 'nominal' ? (
                  <Line type="monotone" dataKey="nominal" name="Nominal" stroke="#34d399" strokeWidth={2} dot={false} />
                ) : (
                  <Line type="monotone" dataKey="real" name="Real" stroke="#38bdf8" strokeWidth={2} dot={false} />
                )}
              </LineChart>
            )}
          </ResponsiveContainer>
        </div>
      ) : null}
    </div>
  )
}
