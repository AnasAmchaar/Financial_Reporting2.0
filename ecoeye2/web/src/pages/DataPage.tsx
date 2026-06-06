import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
} from '@tanstack/react-table'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { apiFetch } from '../lib/api'

type TablesResp = { tables: { name: string; editable: boolean; has_real: boolean }[] }
type RowsResp = {
  table: string
  rows: Record<string, unknown>[]
  total: number
  limit: number
  offset: number
}

export function DataPage() {
  const [tables, setTables] = useState<TablesResp['tables']>([])
  const [table, setTable] = useState('')
  const [offset, setOffset] = useState(0)
  const limit = 50
  const [rows, setRows] = useState<Record<string, unknown>[]>([])
  const [total, setTotal] = useState(0)
  const [pending, setPending] = useState<Record<number, Record<string, unknown>>>({})
  const [msg, setMsg] = useState<{ type: 'ok' | 'err' | 'info'; text: string } | null>(null)

  const loadTables = useCallback(async () => {
    const r = await apiFetch<TablesResp>('/api/v1/tables')
    setTables(r.tables)
    setTable((t) => t || (r.tables[0]?.name ?? ''))
  }, [])

  const loadRows = useCallback(async () => {
    if (!table) return
    const r = await apiFetch<RowsResp>(
      `/api/v1/tables/${encodeURIComponent(table)}/rows?limit=${limit}&offset=${offset}`,
    )
    setRows(r.rows)
    setTotal(r.total)
    setPending({})
  }, [table, offset])

  useEffect(() => {
    loadTables().catch((e) => setMsg({ type: 'err', text: String(e instanceof Error ? e.message : e) }))
  }, [loadTables])

  useEffect(() => {
    if (table)
      loadRows().catch((e) => setMsg({ type: 'err', text: String(e.message) }))
  }, [table, offset, loadRows])

  const meta = tables.find((t) => t.name === table)
  const totalPages = Math.max(1, Math.ceil(total / limit))
  const currentPage = Math.floor(offset / limit) + 1

  const columns = useMemo<ColumnDef<Record<string, unknown>>[]>(() => {
    if (!rows.length) return []
    const keys = Object.keys(rows[0]).filter((k) => k !== '_rowid')
    return keys.map((key) => ({
      accessorKey: key,
      header: key,
      cell: (info) => {
        const row = info.row.original
        const rid = row._rowid as number
        const v =
          pending[rid]?.[key] !== undefined ? pending[rid][key] : info.getValue()
        if (!meta?.editable || key === '_rowid') {
          // Format numbers nicely for read-only cells
          if (typeof v === 'number') return v.toLocaleString(undefined, { maximumFractionDigits: 2 })
          return String(v ?? '')
        }
        return (
          <input
            className="w-full min-w-[4rem] rounded-lg border border-slate-700/60 bg-slate-950/80 px-2 py-1 text-xs text-slate-200 outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/30 transition"
            value={v === null || v === undefined ? '' : String(v)}
            onChange={(e) => {
              const raw = e.target.value
              let parsed: unknown = raw
              if (raw === '') parsed = null
              else if (!Number.isNaN(Number(raw)) && raw.trim() !== '') parsed = Number(raw)
              setPending((p) => ({
                ...p,
                [rid]: { ...(p[rid] ?? {}), [key]: parsed },
              }))
            }}
          />
        )
      },
    }))
  }, [rows, pending, meta?.editable])

  const tableModel = useReactTable({
    data: rows,
    columns,
    getCoreRowModel: getCoreRowModel(),
  })

  async function save() {
    if (!meta?.editable) return
    const updates: { rowid: number; column: string; value: unknown }[] = []
    for (const [ridStr, cols] of Object.entries(pending)) {
      const rid = Number(ridStr)
      for (const [col, val] of Object.entries(cols)) {
        updates.push({ rowid: rid, column: col, value: val })
      }
    }
    if (!updates.length) {
      setMsg({ type: 'info', text: 'No changes to save.' })
      return
    }
    try {
      await apiFetch('/api/v1/tables/' + encodeURIComponent(table) + '/rows', {
        method: 'PATCH',
        body: JSON.stringify({ updates }),
      })
      setMsg({ type: 'ok', text: `Saved ${updates.length} cell(s) successfully.` })
      await loadRows()
    } catch (e) {
      setMsg({ type: 'err', text: e instanceof Error ? e.message : String(e) })
    }
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="section-title">Data</h1>
        <p className="section-subtitle mt-1">
          Paginated SQLite rows. Edits apply to <strong className="text-slate-200">raw</strong> tables only;{' '}
          <code className="text-emerald-400/80">*_real</code> is read-only.
        </p>
      </div>

      <div className="app-card flex flex-wrap items-end gap-4 p-5">
        <div className="min-w-[240px]">
          <label className="mb-1.5 block text-xs font-medium text-slate-500">Table</label>
          <select
            value={table}
            onChange={(e) => {
              setTable(e.target.value)
              setOffset(0)
            }}
            className="app-input"
          >
            {tables.map((t) => (
              <option key={t.name} value={t.name}>
                {t.name}
                {t.has_real ? ' (+ real)' : ''}
                {!t.editable ? ' [ro]' : ''}
              </option>
            ))}
          </select>
        </div>
        {meta?.editable ? (
          <button
            type="button"
            onClick={save}
            className="btn-primary"
          >
            Save changes
          </button>
        ) : null}
        <div className="badge-muted flex items-center gap-2">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-slate-500">
            <ellipse cx="12" cy="5" rx="9" ry="3" /><path d="M3 5V19A9 3 0 0 0 21 19V5" /><path d="M3 12A9 3 0 0 0 21 12" />
          </svg>
          {total.toLocaleString()} rows · page {currentPage} / {totalPages}
        </div>
      </div>

      {msg ? (
        <div className={
          msg.type === 'ok' ? 'banner-success' :
          msg.type === 'err' ? 'banner-error' :
          'app-card border-slate-600/40 p-3 text-sm text-slate-300'
        }>
          {msg.text}
        </div>
      ) : null}

      <div className="app-card overflow-x-auto rounded-xl">
        <table className="app-table">
          <thead>
            {tableModel.getHeaderGroups().map((hg) => (
              <tr key={hg.id}>
                {hg.headers.map((h) => (
                  <th key={h.id}>
                    {flexRender(h.column.columnDef.header, h.getContext())}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {tableModel.getRowModel().rows.map((row) => (
              <tr key={row.id}>
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="flex items-center gap-2">
        <button
          type="button"
          disabled={offset === 0}
          onClick={() => setOffset(0)}
          className="btn-secondary text-xs"
          title="First page"
        >
          ««
        </button>
        <button
          type="button"
          disabled={offset === 0}
          onClick={() => setOffset((o) => Math.max(0, o - limit))}
          className="btn-secondary text-xs"
        >
          ← Prev
        </button>
        <div className="flex gap-1">
          {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
            let page: number
            if (totalPages <= 5) {
              page = i + 1
            } else if (currentPage <= 3) {
              page = i + 1
            } else if (currentPage >= totalPages - 2) {
              page = totalPages - 4 + i
            } else {
              page = currentPage - 2 + i
            }
            return (
              <button
                key={page}
                type="button"
                onClick={() => setOffset((page - 1) * limit)}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                  page === currentPage
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                    : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200 border border-transparent'
                }`}
              >
                {page}
              </button>
            )
          })}
        </div>
        <button
          type="button"
          disabled={offset + limit >= total}
          onClick={() => setOffset((o) => o + limit)}
          className="btn-secondary text-xs"
        >
          Next →
        </button>
        <button
          type="button"
          disabled={offset + limit >= total}
          onClick={() => setOffset((totalPages - 1) * limit)}
          className="btn-secondary text-xs"
          title="Last page"
        >
          »»
        </button>
      </div>
    </div>
  )
}
