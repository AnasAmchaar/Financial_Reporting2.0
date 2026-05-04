import { useState } from 'react'
import { apiFetch } from '../lib/api'

type EtlResp = {
  ok: boolean
  message?: string | null
  tables: { table: string; ok: boolean; rows: number; error?: string | null }[]
}

export function IngestPage() {
  const [busy, setBusy] = useState(false)
  const [log, setLog] = useState<string[]>([])
  const [filename, setFilename] = useState('')
  const [etlMode, setEtlMode] = useState<'all' | 'file'>('all')

  const push = (m: string) => setLog((l) => [...l, `${new Date().toISOString().slice(11, 19)}  ${m}`])

  async function onUpload(ev: React.ChangeEvent<HTMLInputElement>) {
    const f = ev.target.files?.[0]
    if (!f) return
    setBusy(true)
    push(`Uploading ${f.name}…`)
    try {
      const fd = new FormData()
      fd.append('file', f)
      const res = await fetch('/api/v1/uploads', {
        method: 'POST',
        body: fd,
        headers: import.meta.env.VITE_ECOEYE2_API_KEY
          ? { 'X-Api-Key': import.meta.env.VITE_ECOEYE2_API_KEY as string }
          : undefined,
      })
      if (!res.ok) throw new Error(await res.text())
      const j = (await res.json()) as { filename: string }
      setFilename(j.filename)
      push(`Saved as ${j.filename} (register in config/settings.py SOURCES if new workbook).`)
    } catch (e) {
      push(`Upload error: ${e instanceof Error ? e.message : String(e)}`)
    } finally {
      setBusy(false)
    }
  }

  async function runEtl() {
    setBusy(true)
    push('Running ETL…')
    try {
      const body =
        etlMode === 'file'
          ? { mode: 'file' as const, filename, tables: [] }
          : { mode: 'all' as const, tables: [] }
      const r = await apiFetch<EtlResp>('/api/v1/pipeline/etl', {
        method: 'POST',
        body: JSON.stringify(body),
      })
      if (!r.ok) push(`ETL failed: ${r.message ?? 'see tables'}`)
      for (const t of r.tables) {
        push(`${t.ok ? 'OK' : 'ERR'}  ${t.table}  (${t.rows} rows) ${t.error ?? ''}`)
      }
    } catch (e) {
      push(`ETL error: ${e instanceof Error ? e.message : String(e)}`)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <h1 className="section-title">Ingest</h1>
      <p className="section-subtitle">
        Upload Excel to <code className="text-emerald-400/90">data/raw</code>. Registered filenames in{' '}
        <code className="text-emerald-400/90">SOURCES</code> are processed by ETL into SQLite.
      </p>

      <div className="app-card p-5">
        <label className="mb-2 block text-sm font-medium text-slate-300">Upload workbook</label>
        <input
          type="file"
          accept=".xlsx,.xls"
          disabled={busy}
          onChange={onUpload}
          className="block w-full text-sm text-slate-300 file:mr-4 file:rounded-lg file:border-0 file:bg-emerald-600 file:px-4 file:py-2 file:text-sm file:font-medium file:text-white hover:file:bg-emerald-500"
        />
        {filename ? (
          <p className="mt-3 text-xs text-slate-500">
            Last upload: <span className="text-slate-300">{filename}</span>
          </p>
        ) : null}
      </div>

      <div className="app-card p-5">
        <div className="mb-3 flex flex-wrap gap-4">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="radio"
              checked={etlMode === 'all'}
              onChange={() => setEtlMode('all')}
            />
            Run ETL (all SOURCES)
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="radio"
              checked={etlMode === 'file'}
              onChange={() => setEtlMode('file')}
            />
            Run ETL for one file
          </label>
        </div>
        {etlMode === 'file' ? (
          <input
            value={filename}
            onChange={(e) => setFilename(e.target.value)}
            placeholder="Exact filename in data/raw (e.g. DISLOG_BR_Template 08-2023.xlsx)"
            className="app-input mb-3"
          />
        ) : null}
        <button
          type="button"
          disabled={busy || (etlMode === 'file' && !filename)}
          onClick={runEtl}
          className="btn-primary"
        >
          {busy ? 'Working…' : 'Run ETL'}
        </button>
      </div>

      <div className="app-card bg-black/45 p-4 font-mono text-xs text-slate-300">
        {log.length === 0 ? <span className="text-slate-600">Log output…</span> : log.map((l, i) => <div key={i}>{l}</div>)}
      </div>
    </div>
  )
}
