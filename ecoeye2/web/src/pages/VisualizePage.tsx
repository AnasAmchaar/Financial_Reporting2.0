import { useEffect, useMemo, useState } from 'react'
import {
  CartesianGrid,
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

function toCsv(rows: SeriesResp['points'], mode: string) {
  const header =
    mode === 'both'
      ? 'period,nominal,real'
      : mode === 'real'
        ? 'period,real'
        : 'period,nominal'
  const lines = [header]
  for (const p of rows) {
    if (mode === 'both') lines.push(`${p.period},${p.nominal ?? ''},${p.real ?? ''}`)
    else if (mode === 'real') lines.push(`${p.period},${p.real ?? ''}`)
    else lines.push(`${p.period},${p.nominal ?? ''}`)
  }
  return lines.join('\n')
}

export function VisualizePage() {
  const [table, setTable] = useState('data_reel')
  const [mode, setMode] = useState<'nominal' | 'real' | 'both'>('both')
  const [groupBy, setGroupBy] = useState<'month' | 'partner' | 'channel'>('month')
  const [data, setData] = useState<SeriesResp['points']>([])
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

  const chartData = useMemo(
    () =>
      data.map((p) => ({
        ...p,
        nominal: p.nominal ?? undefined,
        real: p.real ?? undefined,
      })),
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

  return (
    <div className="space-y-6">
      <h1 className="section-title">Visualize</h1>
      <p className="section-subtitle">
        Compare <strong className="text-slate-200">before</strong> (nominal) and{' '}
        <strong className="text-slate-200">after</strong> (inflation-adjusted) using{' '}
        <code className="text-emerald-400/80">*_real</code> when available.
      </p>

      <div className="app-card flex flex-wrap items-center gap-3 p-4">
        <div>
          <label className="mb-1 block text-xs text-slate-500">Dataset</label>
          <input
            value={table}
            onChange={(e) => setTable(e.target.value)}
            className="app-input"
          />
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
        <button
          type="button"
          onClick={downloadCsv}
          className="btn-secondary mt-5"
        >
          Export CSV
        </button>
      </div>

      {err ? <div className="text-sm text-red-400">{err}</div> : null}

      <div className="app-card h-[420px] w-full p-3">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="period" tick={{ fill: '#94a3b8', fontSize: 11 }} angle={-35} textAnchor="end" height={70} />
            <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} />
            <Tooltip
              contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: 8 }}
              labelStyle={{ color: '#e2e8f0' }}
            />
            <Legend />
            {(mode === 'nominal' || mode === 'both') && (
              <Line type="monotone" dataKey="nominal" name="Nominal" stroke="#34d399" strokeWidth={2} dot={false} />
            )}
            {(mode === 'real' || mode === 'both') && (
              <Line type="monotone" dataKey="real" name="Real" stroke="#38bdf8" strokeWidth={2} dot={false} />
            )}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
