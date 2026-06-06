import { useCallback, useEffect, useMemo, useState } from 'react'
import { apiFetch } from '../lib/api'

type TableInfo = { name: string; editable: boolean; has_real: boolean }

type Stats = {
  mean: number
  median: number
  std: number
  q1: number
  q3: number
  iqr: number
  lower_bound: number
  upper_bound: number
  total_rows: number
}

type OutlierRow = {
  rowid: number
  value: number
  z_score: number
  deviation: number
  row_preview: Record<string, unknown>
}

type DetectResp = {
  table: string
  column: string
  method: string
  sensitivity: number
  stats: Stats
  outliers: OutlierRow[]
  total_rows: number
  outlier_count: number
  message?: string
}

function fmt(n: number) {
  return n.toLocaleString(undefined, { maximumFractionDigits: 2 })
}

const PAGE_SIZE = 25

export function OutliersPage() {
  const [tables, setTables] = useState<TableInfo[]>([])
  const [table, setTable] = useState('data_reel')
  const [columns, setColumns] = useState<string[]>([])
  const [column, setColumn] = useState('amount')
  const [method, setMethod] = useState<'iqr' | 'zscore'>('iqr')
  const [sensitivity, setSensitivity] = useState(1.5)
  const [result, setResult] = useState<DetectResp | null>(null)
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [busy, setBusy] = useState(false)
  const [actionBusy, setActionBusy] = useState(false)
  const [banner, setBanner] = useState<{ type: 'ok' | 'err'; text: string } | null>(null)
  const [showConfirm, setShowConfirm] = useState<{ action: string; label: string } | null>(null)
  const [customValue, setCustomValue] = useState('')
  const [page, setPage] = useState(0)

  // Load tables
  useEffect(() => {
    apiFetch<{ tables: TableInfo[] }>('/api/v1/tables')
      .then((r) => {
        setTables(r.tables)
        if (!r.tables.find((t) => t.name === table) && r.tables.length > 0) {
          setTable(r.tables[0].name)
        }
      })
      .catch(() => {})
  }, [])

  // Load columns when table changes
  useEffect(() => {
    if (!table) return
    apiFetch<{ rows: Record<string, unknown>[]; total: number }>(
      `/api/v1/tables/${encodeURIComponent(table)}/rows?limit=1`
    )
      .then((r) => {
        if (r.rows.length > 0) {
          const cols = Object.keys(r.rows[0]).filter((k) => k !== '_rowid')
          setColumns(cols)
          if (!cols.includes(column)) setColumn(cols.find((c) => c === 'amount') || cols[0] || '')
        }
      })
      .catch(() => {})
  }, [table])

  const detect = useCallback(async () => {
    setBusy(true)
    setBanner(null)
    setResult(null)
    setSelected(new Set())
    setPage(0)
    try {
      const resp = await apiFetch<DetectResp>('/api/v1/outliers/detect', {
        method: 'POST',
        body: JSON.stringify({ table, column, method, sensitivity }),
      })
      setResult(resp)
      if (resp.outlier_count === 0) {
        setBanner({ type: 'ok', text: 'No outliers detected with the current settings.' })
      }
    } catch (e) {
      setBanner({ type: 'err', text: e instanceof Error ? e.message : String(e) })
    } finally {
      setBusy(false)
    }
  }, [table, column, method, sensitivity])

  // Paginated view of outliers
  const totalPages = result ? Math.max(1, Math.ceil(result.outliers.length / PAGE_SIZE)) : 1
  const pagedOutliers = useMemo(() => {
    if (!result) return []
    const start = page * PAGE_SIZE
    return result.outliers.slice(start, start + PAGE_SIZE)
  }, [result, page])

  // Preview columns from first outlier
  const previewCols = useMemo(() => {
    if (!result || result.outliers.length === 0) return []
    return Object.keys(result.outliers[0].row_preview)
      .filter((k) => k !== column)
      .slice(0, 4)
  }, [result, column])

  const toggleRow = (rid: number) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(rid)) next.delete(rid)
      else next.add(rid)
      return next
    })
  }

  const togglePageAll = () => {
    if (!result) return
    const pageRids = pagedOutliers.map((o) => o.rowid)
    const allSelected = pageRids.every((r) => selected.has(r))
    setSelected((prev) => {
      const next = new Set(prev)
      if (allSelected) {
        pageRids.forEach((r) => next.delete(r))
      } else {
        pageRids.forEach((r) => next.add(r))
      }
      return next
    })
  }

  const selectAll = () => {
    if (!result) return
    if (selected.size === result.outliers.length) {
      setSelected(new Set())
    } else {
      setSelected(new Set(result.outliers.map((o) => o.rowid)))
    }
  }

  const executeAction = async (action: string) => {
    if (selected.size === 0) return
    setActionBusy(true)
    setBanner(null)
    setShowConfirm(null)
    try {
      const body: Record<string, unknown> = {
        table,
        column,
        rowids: Array.from(selected),
        action,
      }
      if (action === 'replace_custom') {
        body.custom_value = parseFloat(customValue)
      }
      const resp = await apiFetch<{ ok: boolean; detail: string }>('/api/v1/outliers/action', {
        method: 'POST',
        body: JSON.stringify(body),
      })
      setBanner({ type: 'ok', text: resp.detail })
      await detect()
    } catch (e) {
      setBanner({ type: 'err', text: e instanceof Error ? e.message : String(e) })
    } finally {
      setActionBusy(false)
    }
  }

  const severityBadge = (z: number) => {
    if (z >= 5) return <span className="inline-flex items-center rounded-full border border-red-500/30 bg-red-500/10 px-2 py-0.5 text-[10px] font-bold text-red-400">Extreme</span>
    if (z >= 3) return <span className="inline-flex items-center rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-[10px] font-bold text-amber-400">High</span>
    return <span className="inline-flex items-center rounded-full border border-slate-600/50 bg-slate-700/30 px-2 py-0.5 text-[10px] font-bold text-slate-400">Moderate</span>
  }

  const isEditable = tables.find((t) => t.name === table)?.editable ?? false
  const hasResults = result && result.outliers.length > 0

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      {/* Header */}
      <div>
        <h1 className="section-title">Outlier Management</h1>
        <p className="section-subtitle mt-1">
          Detect anomalous data points using statistical methods. Review, replace, or drop flagged rows.
        </p>
      </div>

      {banner && (
        <div className={banner.type === 'ok' ? 'banner-success' : 'banner-error'}>{banner.text}</div>
      )}

      {/* ─── Detection Settings ────────────────────────────────── */}
      <div className="app-card p-5 space-y-5">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-200 tracking-wide">Detection Settings</h2>
          <div className="badge-muted">
            {method === 'iqr' ? `${sensitivity.toFixed(1)}× IQR` : `|z| > ${sensitivity.toFixed(1)}`}
          </div>
        </div>

        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Table</label>
            <select value={table} onChange={(e) => setTable(e.target.value)} className="app-input">
              {tables.map((t) => (
                <option key={t.name} value={t.name}>{t.name}{!t.editable ? ' [ro]' : ''}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Column</label>
            <select value={column} onChange={(e) => setColumn(e.target.value)} className="app-input">
              {columns.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Method</label>
            <select value={method} onChange={(e) => setMethod(e.target.value as 'iqr' | 'zscore')} className="app-input">
              <option value="iqr">IQR (Interquartile Range)</option>
              <option value="zscore">Z-Score</option>
            </select>
          </div>
          <div>
            <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              Sensitivity
            </label>
            <div className="flex items-center gap-3">
              <input
                type="range" min="0.5" max="5" step="0.1"
                value={sensitivity}
                onChange={(e) => setSensitivity(parseFloat(e.target.value))}
                className="flex-1 accent-emerald-500 h-2"
              />
              <span className="w-10 text-right text-sm font-mono font-semibold text-emerald-400">{sensitivity.toFixed(1)}</span>
            </div>
            <div className="mt-1 flex justify-between text-[10px] text-slate-600">
              <span>Strict</span><span>Lenient</span>
            </div>
          </div>
        </div>

        <button type="button" onClick={detect} disabled={busy || !table || !column} className="btn-primary">
          {busy ? (
            <span className="flex items-center gap-2">
              <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Scanning…
            </span>
          ) : 'Run Detection'}
        </button>
      </div>

      {/* ─── Stats KPIs ────────────────────────────────────────── */}
      {result && result.stats && Object.keys(result.stats).length > 0 && (
        <div className="grid gap-3 grid-cols-2 sm:grid-cols-3 lg:grid-cols-6">
          {[
            { label: 'Mean', value: fmt(result.stats.mean), color: 'text-white' },
            { label: 'Median', value: fmt(result.stats.median), color: 'text-white' },
            { label: 'Std Dev', value: fmt(result.stats.std), color: 'text-slate-300' },
            { label: 'Lower', value: fmt(result.stats.lower_bound), color: 'text-sky-400' },
            { label: 'Upper', value: fmt(result.stats.upper_bound), color: 'text-sky-400' },
            {
              label: 'Outliers',
              value: `${result.outlier_count}`,
              sub: `of ${result.total_rows}`,
              color: result.outlier_count > 0 ? 'text-amber-400' : 'text-emerald-400',
            },
          ].map((s) => (
            <div key={s.label} className="app-card p-3 text-center">
              <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">{s.label}</div>
              <div className={`mt-1 text-base font-bold tabular-nums ${s.color}`}>{s.value}</div>
              {'sub' in s && s.sub && <div className="text-[10px] text-slate-600">{s.sub}</div>}
            </div>
          ))}
        </div>
      )}

      {/* ─── Action bar ────────────────────────────────────────── */}
      {hasResults && isEditable && (
        <div className="app-card p-4">
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2 mr-auto">
              <button type="button" onClick={selectAll} className="text-xs text-emerald-400 hover:text-emerald-300 font-medium transition-colors">
                {selected.size === result!.outliers.length ? 'Deselect all' : `Select all ${result!.outlier_count}`}
              </button>
              <span className="text-[11px] text-slate-500">
                {selected.size > 0 ? `${selected.size} selected` : 'None selected'}
              </span>
            </div>

            <button type="button" disabled={selected.size === 0 || actionBusy}
              onClick={() => setShowConfirm({ action: 'replace_median', label: 'Replace with Median' })}
              className="btn-secondary !py-1.5 !px-3 text-xs">
              Median
            </button>
            <button type="button" disabled={selected.size === 0 || actionBusy}
              onClick={() => setShowConfirm({ action: 'replace_mean', label: 'Replace with Mean' })}
              className="btn-secondary !py-1.5 !px-3 text-xs">
              Mean
            </button>
            <div className="flex items-center gap-1">
              <input type="number" value={customValue} onChange={(e) => setCustomValue(e.target.value)}
                placeholder="Custom" disabled={selected.size === 0}
                className="app-input !w-24 !py-1.5 text-xs" />
              <button type="button" disabled={selected.size === 0 || actionBusy || !customValue}
                onClick={() => setShowConfirm({ action: 'replace_custom', label: `Replace with ${customValue}` })}
                className="btn-secondary !py-1.5 !px-3 text-xs">
                Set
              </button>
            </div>
            <button type="button" disabled={selected.size === 0 || actionBusy}
              onClick={() => setShowConfirm({ action: 'drop', label: 'Drop Rows' })}
              className="btn-danger !py-1.5 !px-3 text-xs">
              Drop
            </button>
          </div>
        </div>
      )}

      {/* ─── Outlier table (paginated) ─────────────────────────── */}
      {hasResults && (
        <div className="app-card overflow-hidden rounded-xl">
          <table className="app-table">
            <thead>
              <tr>
                {isEditable && (
                  <th className="!w-10 text-center">
                    <input type="checkbox"
                      checked={pagedOutliers.length > 0 && pagedOutliers.every((o) => selected.has(o.rowid))}
                      onChange={togglePageAll} className="accent-emerald-500" />
                  </th>
                )}
                <th>Value</th>
                <th>Z-Score</th>
                <th>Severity</th>
                {previewCols.map((k) => <th key={k}>{k}</th>)}
              </tr>
            </thead>
            <tbody>
              {pagedOutliers.map((o) => (
                <tr key={o.rowid} className={selected.has(o.rowid) ? '!bg-emerald-950/30' : ''}>
                  {isEditable && (
                    <td className="text-center">
                      <input type="checkbox" checked={selected.has(o.rowid)}
                        onChange={() => toggleRow(o.rowid)} className="accent-emerald-500" />
                    </td>
                  )}
                  <td className="font-mono font-bold text-amber-300">{fmt(o.value)}</td>
                  <td className="font-mono text-slate-300">{o.z_score.toFixed(2)}</td>
                  <td>{severityBadge(o.z_score)}</td>
                  {previewCols.map((k) => (
                    <td key={k} className="max-w-[140px] truncate text-slate-400 text-[12px]">
                      {String(o.row_preview[k] ?? '—')}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>

          {/* Pagination footer */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between border-t border-slate-800/60 px-4 py-3">
              <span className="text-xs text-slate-500">
                Showing {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, result!.outlier_count)} of {result!.outlier_count}
              </span>
              <div className="flex items-center gap-1">
                <button type="button" disabled={page === 0} onClick={() => setPage(0)}
                  className="rounded-lg px-2 py-1 text-xs text-slate-400 hover:bg-slate-800 disabled:opacity-30 transition-colors">
                  ««
                </button>
                <button type="button" disabled={page === 0} onClick={() => setPage((p) => p - 1)}
                  className="rounded-lg px-2 py-1 text-xs text-slate-400 hover:bg-slate-800 disabled:opacity-30 transition-colors">
                  ‹
                </button>
                {Array.from({ length: Math.min(7, totalPages) }, (_, i) => {
                  let p: number
                  if (totalPages <= 7) p = i
                  else if (page < 3) p = i
                  else if (page >= totalPages - 4) p = totalPages - 7 + i
                  else p = page - 3 + i
                  return (
                    <button key={p} type="button" onClick={() => setPage(p)}
                      className={`rounded-lg px-2.5 py-1 text-xs font-medium transition-colors ${
                        p === page
                          ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                          : 'text-slate-500 hover:bg-slate-800 hover:text-slate-300 border border-transparent'
                      }`}>
                      {p + 1}
                    </button>
                  )
                })}
                <button type="button" disabled={page >= totalPages - 1} onClick={() => setPage((p) => p + 1)}
                  className="rounded-lg px-2 py-1 text-xs text-slate-400 hover:bg-slate-800 disabled:opacity-30 transition-colors">
                  ›
                </button>
                <button type="button" disabled={page >= totalPages - 1} onClick={() => setPage(totalPages - 1)}
                  className="rounded-lg px-2 py-1 text-xs text-slate-400 hover:bg-slate-800 disabled:opacity-30 transition-colors">
                  »»
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ─── Confirmation modal ────────────────────────────────── */}
      {showConfirm && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/70 backdrop-blur-sm">
          <div className="app-card mx-4 w-full max-w-md p-6 shadow-2xl">
            <h3 className="text-lg font-bold text-white">Confirm Action</h3>
            <p className="mt-3 text-sm text-slate-400 leading-relaxed">
              Are you sure you want to <strong className="text-slate-200">{showConfirm.label}</strong> on{' '}
              <strong className="text-amber-400">{selected.size}</strong> row(s) in <code className="text-emerald-400">{table}.{column}</code>?
            </p>
            {showConfirm.action === 'drop' && (
              <div className="mt-3 rounded-lg border border-red-500/30 bg-red-950/30 px-3 py-2 text-xs text-red-300">
                ⚠ This permanently deletes the selected rows from the database.
              </div>
            )}
            <div className="mt-5 flex justify-end gap-3">
              <button type="button" onClick={() => setShowConfirm(null)} className="btn-secondary">Cancel</button>
              <button type="button" onClick={() => executeAction(showConfirm.action)}
                className={showConfirm.action === 'drop' ? 'btn-danger' : 'btn-primary'} disabled={actionBusy}>
                {actionBusy ? 'Processing…' : showConfirm.label}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ─── Empty state ──────────────────────────────────────── */}
      {!result && !busy && (
        <div className="app-card flex flex-col items-center justify-center py-16 text-center">
          <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-slate-800/60 border border-slate-700/50">
            <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-slate-500">
              <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3" /><path d="M12 9v4" /><path d="M12 17h.01" />
            </svg>
          </div>
          <p className="text-sm font-medium text-slate-400">No detection run yet</p>
          <p className="mt-1 text-xs text-slate-600">Configure settings above and click "Run Detection" to scan for outliers.</p>
        </div>
      )}
    </div>
  )
}
