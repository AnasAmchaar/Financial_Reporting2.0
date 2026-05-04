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
  const [msg, setMsg] = useState('')

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
    loadTables().catch((e) => setMsg(String(e instanceof Error ? e.message : e)))
  }, [loadTables])

  useEffect(() => {
    if (table)
      loadRows().catch((e) => setMsg(String(e.message)))
  }, [table, offset, loadRows])

  const meta = tables.find((t) => t.name === table)

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
        if (!meta?.editable || key === '_rowid') return String(v ?? '')
        return (
          <input
            className="w-full min-w-[4rem] rounded border border-slate-700 bg-slate-950 px-1 py-0.5 text-xs"
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
      setMsg('No changes to save.')
      return
    }
    try {
      await apiFetch('/api/v1/tables/' + encodeURIComponent(table) + '/rows', {
        method: 'PATCH',
        body: JSON.stringify({ updates }),
      })
      setMsg(`Saved ${updates.length} cell(s).`)
      await loadRows()
    } catch (e) {
      setMsg(e instanceof Error ? e.message : String(e))
    }
  }

  return (
    <div className="space-y-5">
      <h1 className="section-title">Data</h1>
      <p className="section-subtitle">
        Paginated SQLite rows. Edits apply to <strong className="text-slate-200">raw</strong> tables only;{' '}
        <code className="text-emerald-400/80">*_real</code> is read-only.
      </p>

      <div className="app-card flex flex-wrap items-end gap-3 p-4">
        <div>
          <label className="mb-1 block text-xs text-slate-500">Table</label>
          <select
            value={table}
            onChange={(e) => {
              setTable(e.target.value)
              setOffset(0)
            }}
            className="app-input min-w-[240px]"
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
        <div className="badge-muted">
          {total} rows · page {Math.floor(offset / limit) + 1} / {Math.max(1, Math.ceil(total / limit))}
        </div>
      </div>

      {msg ? <div className="text-sm text-amber-400">{msg}</div> : null}

      <div className="app-card overflow-x-auto rounded-lg">
        <table className="w-full min-w-max border-collapse text-left text-xs">
          <thead>
            {tableModel.getHeaderGroups().map((hg) => (
              <tr key={hg.id} className="border-b border-slate-800 bg-slate-900">
                {hg.headers.map((h) => (
                  <th key={h.id} className="px-2 py-2 font-medium text-slate-400">
                    {flexRender(h.column.columnDef.header, h.getContext())}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {tableModel.getRowModel().rows.map((row) => (
              <tr key={row.id} className="border-b border-slate-800/80 hover:bg-slate-900/50">
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id} className="px-2 py-1 align-top text-slate-200">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex gap-2">
        <button
          type="button"
          disabled={offset === 0}
          onClick={() => setOffset((o) => Math.max(0, o - limit))}
          className="btn-secondary"
        >
          Previous
        </button>
        <button
          type="button"
          disabled={offset + limit >= total}
          onClick={() => setOffset((o) => o + limit)}
          className="btn-secondary"
        >
          Next
        </button>
      </div>
    </div>
  )
}
