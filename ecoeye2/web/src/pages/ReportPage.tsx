import { useEffect, useState, useMemo } from 'react'
import {
  Bar,
  Area,
  Line,
  CartesianGrid,
  ComposedChart,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import ReactMarkdown from 'react-markdown'
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

type EvaPoint = {
  period: string
  nopat: number
  invested_capital: number
  wacc: number
  capital_charge: number
  eva: number
}

type VpmfPoint = {
  period: string
  nominal: number
  price_effect: number
  volume_effect: number
  delta: number
  delta_price: number
  delta_volume: number
}

type DimensionRow = {
  dim: string
  value: string
  nominal: number
  real: number | null
}

function fmt(n: number | null | undefined) {
  if (n == null) return '—'
  return n.toLocaleString(undefined, { maximumFractionDigits: 0 })
}

function fmtPct(n: number | null | undefined) {
  if (n == null) return '—'
  return `${(n * 100).toFixed(1)}%`
}

export function ReportPage() {
  const [table, setTable] = useState('data_reel')
  const [summary, setSummary] = useState<ReportingSummary | null>(null)
  const [evaData, setEvaData] = useState<EvaPoint[]>([])
  const [vpmfData, setVpmfData] = useState<VpmfPoint[]>([])
  const [topPartners, setTopPartners] = useState<DimensionRow[]>([])
  const [topChannels, setTopChannels] = useState<DimensionRow[]>([])
  
  // AI Narrative states
  const [aiNarrative, setAiNarrative] = useState<string>('')
  const [isGeneratingAi, setIsGeneratingAi] = useState<boolean>(false)
  const [aiError, setAiError] = useState<string>('')
  const [err, setErr] = useState('')

  // Fetch report data
  const loadReportData = async () => {
    setErr('')
    try {
      const q = new URLSearchParams({ table })
      
      // Fetch summary
      const sum = await apiFetch<ReportingSummary>(`/api/v1/reporting/summary?${q}`)
      setSummary(sum)

      // Fetch EVA
      const eva = await apiFetch<{ points: EvaPoint[] }>('/api/v1/reporting/eva-demo').catch(() => ({ points: [] }))
      setEvaData(eva.points || [])

      // Fetch VPMF
      const vpmf = await apiFetch<{ points: VpmfPoint[] }>(`/api/v1/reporting/vpmf-demo?${q}`).catch(() => ({ points: [] }))
      setVpmfData(vpmf.points || [])

      // Fetch Top Partners and Channels
      const partners = await apiFetch<{ rows: DimensionRow[] }>(`/api/v1/reporting/top-dimensions?table=${table}&dim=partner&limit=5`).catch(() => ({ rows: [] }))
      setTopPartners(partners.rows || [])

      const channels = await apiFetch<{ rows: DimensionRow[] }>(`/api/v1/reporting/top-dimensions?table=${table}&dim=channel&limit=5`).catch(() => ({ rows: [] }))
      setTopChannels(channels.rows || [])
    } catch (e: any) {
      setErr(e.message || String(e))
    }
  }

  useEffect(() => {
    loadReportData()
  }, [table])

  // Sync state for LLM context
  useEffect(() => {
    if (summary) {
      window.__ECOEYE_CONTEXT__ = {
        page: 'AutomatedReport',
        table,
        summary,
        eva_summary: evaData.length ? {
          total_nopat: evaData.reduce((acc, p) => acc + p.nopat, 0),
          total_eva: evaData.reduce((acc, p) => acc + p.eva, 0),
          wacc: evaData[0]?.wacc
        } : null,
        vpmf_summary: vpmfData.length ? vpmfData[vpmfData.length - 1] : null,
        top_partners: topPartners.slice(0, 3)
      }
    }
  }, [summary, evaData, vpmfData, topPartners])

  // Trigger AI Briefing Narrative Generation
  const generateAiNarrative = async () => {
    if (!summary) return
    setIsGeneratingAi(true)
    setAiError('')
    
    try {
      const dataPayload = {
        table,
        summary,
        eva: evaData.map(p => ({ period: p.period, nopat: p.nopat, eva: p.eva, wacc: p.wacc })),
        vpmf: vpmfData.map(p => ({ period: p.period, nominal: p.nominal, price_effect: p.price_effect, volume_effect: p.volume_effect })),
        top_partners: topPartners.map(p => ({ name: p.value, nominal: p.nominal, real: p.real })),
        top_channels: topChannels.map(c => ({ name: c.value, nominal: c.nominal, real: c.real }))
      }

      const prompt = `Perform a high-level financial and economic analysis of the following consolidated report. 
Address the key questions an executive would have:
1. **Nominal vs. Real Activity:** What was the overall erosion of purchasing power due to inflation? Identify which logical indicator drove this deflator impact (referencing CPI/PPI split).
2. **Economic Profitability (EVA):** Did the business generate sufficient returns to exceed its WACC? Highlight whether wealth was created or destroyed over the cumulative period.
3. **Growth Drivers (VPMF):** Decompose the growth trends. Is the delta driven primarily by price/inflation effect, or are we seeing true organic volume/mix expansion?
4. **Key Risks & Recommendations:** Cite performance highlights for partners or channels, and suggest action points to mitigate inflation erosion.

Provide a highly polished, professional analysis in Markdown. Use clean headings, bullet points, and tables if useful. Do not include boilerplate introductory text; jump straight into the executive brief.`

      const response = await apiFetch<{ response: string }>('/api/v1/ai/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: prompt,
          context: dataPayload
        })
      })

      setAiNarrative(response.response)
    } catch (e: any) {
      setAiError(e.message || 'Failed to connect with AI analyst. Make sure GEMINI_API_KEY is configured in your backend .env file.')
    } finally {
      setIsGeneratingAi(false)
    }
  }

  // Auto-run AI generator when data first loads and there's no narrative yet
  useEffect(() => {
    if (summary && !aiNarrative && !isGeneratingAi && !aiError) {
      generateAiNarrative()
    }
  }, [summary])

  const printReport = () => {
    window.print()
  }

  return (
    <div className="space-y-8 print:space-y-6 print:p-0">
      
      {/* Header controls (hidden on print) */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between print:hidden">
        <div>
          <h1 className="section-title">Automated Executive Report</h1>
          <p className="section-subtitle mt-1">
            End-to-end purchasing-power aware financial statements, value creation metrics, and automated AI analysis.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2">
            <label className="text-xs text-slate-400 font-medium">Dataset:</label>
            <input 
              value={table} 
              onChange={(e) => setTable(e.target.value)} 
              className="app-input max-w-[140px] px-2.5 py-1.5" 
            />
          </div>
          <button onClick={loadReportData} className="btn-secondary px-3.5 py-1.5 text-xs">
            Reload Data
          </button>
          <button 
            onClick={printReport}
            className="btn-primary flex items-center gap-2 px-4 py-2 font-semibold shadow-lg shadow-emerald-500/20"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M6 9V2h12v7"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect width="12" height="8" x="6" y="14" rx="1" rx="1"/>
            </svg>
            Export Report (PDF)
          </button>
        </div>
      </div>

      {err && (
        <div className="app-card border-red-500/35 bg-red-950/30 p-4 text-sm text-red-200 print:hidden">
          <p className="font-semibold">Unable to compile financial statements</p>
          <p className="mt-1 font-mono text-xs text-red-100/90">{err}</p>
          <p className="mt-2 text-xs">Please run the ETL pipeline from Ingest, fetch macro indicators, and run Apply Real Values from the Adjustments page.</p>
        </div>
      )}

      {/* Main Report Container (Print optimized) */}
      <div className="space-y-8 print:space-y-8">
        
        {/* Document Cover Header (Visible only on print or as standard card) */}
        <div className="hidden print:block border-b-2 border-slate-700 pb-4 mb-6">
          <div className="flex justify-between items-end">
            <div>
              <div className="text-emerald-400 font-extrabold text-2xl tracking-wide uppercase">ECOEYE2 EXECUTIVE REPORT</div>
              <h1 className="text-3xl font-black text-white mt-1">Purchasing-Power Aware Valuation & Capital Performance Dossier</h1>
              <p className="text-slate-400 text-xs mt-1">
                Data Source: <strong className="text-slate-200">{table}</strong> | Base Inflation Anchor Period: <strong className="text-slate-200">2023-12</strong>
              </p>
            </div>
            <div className="text-right">
              <div className="text-xs text-slate-400 uppercase font-bold tracking-wider">Report Generated</div>
              <div className="text-sm font-semibold text-white font-mono">{new Date().toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' })}</div>
            </div>
          </div>
        </div>

        {/* SECTION 1: EXECUTIVE KPI SUMMARY & P&L SPREADS */}
        <div className="space-y-4">
          <h2 className="text-lg font-bold text-slate-200 border-b border-slate-800 pb-2 uppercase tracking-wider flex items-center gap-2">
            <span className="w-1.5 h-4 bg-emerald-500 rounded-sm"></span>
            1. Consolidated Financial Statement & Inflation Gap
          </h2>
          
          {summary ? (
            <>
              {/* KPI Cards Grid */}
              <div className="grid gap-4 grid-cols-2 lg:grid-cols-4">
                <div className="app-card p-4 border-slate-800">
                  <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">Reporting Range</div>
                  <div className="mt-2 text-lg font-bold text-white leading-none">
                    {summary.period_min && summary.period_max
                      ? `${summary.period_min.slice(0, 7)} → ${summary.period_max.slice(0, 7)}`
                      : '—'}
                  </div>
                  <div className="mt-1 text-[10px] text-slate-500 uppercase tracking-tight">Active ledger data</div>
                </div>
                <div className="app-card p-4 border-emerald-500/10">
                  <div className="text-xs font-semibold uppercase tracking-wider text-emerald-400/80">Nominal Turnover</div>
                  <div className="mt-2 text-2xl font-black text-emerald-300 leading-none">{fmt(summary.sum_nominal)} MAD</div>
                  <div className="mt-1 text-[10px] text-slate-500 uppercase tracking-tight">Standard historical sum</div>
                </div>
                <div className="app-card p-4 border-sky-500/10">
                  <div className="text-xs font-semibold uppercase tracking-wider text-sky-400/80">Real Turnover</div>
                  <div className="mt-2 text-2xl font-black text-sky-300 leading-none">
                    {summary.sum_real != null ? `${fmt(summary.sum_real)} MAD` : '—'}
                  </div>
                  <div className="mt-1 text-[10px] text-slate-500 uppercase tracking-tight">Constant-price purchasing power</div>
                </div>
                <div className="app-card p-4 border-slate-700/60 bg-slate-950/20">
                  <div className="text-xs font-semibold uppercase tracking-wider text-slate-400">Erosion (Nominal - Real)</div>
                  <div className="mt-2 text-2xl font-black text-slate-200 leading-none">
                    {summary.inflation_impact != null ? `${fmt(summary.inflation_impact)} MAD` : '—'}
                  </div>
                  <div className="mt-1 text-[10px] text-slate-500 tracking-tight">
                    {summary.sum_nominal && summary.sum_real 
                      ? `Purchasing power loss: ${((1 - (summary.sum_real / summary.sum_nominal)) * 100).toFixed(1)}%` 
                      : 'Inflation drift'}
                  </div>
                </div>
              </div>

              {summary.note && (
                <div className="app-card border-amber-500/25 bg-amber-950/10 p-3 text-xs text-amber-200/80 print:bg-transparent print:border-slate-800">
                  ⚠️ <strong>Reporting Note:</strong> {summary.note}
                </div>
              )}
            </>
          ) : (
            <div className="app-card p-6 text-center text-slate-500 text-sm">
              Loading financial statement summaries...
            </div>
          )}
        </div>

        {/* SECTION 2: CHARTS DECK - EVA & VPMF (SIDE-BY-SIDE ON SCREEN, STACKED ON PRINT) */}
        <div className="grid gap-6 md:grid-cols-2 print:grid-cols-1 print:gap-8">
          
          {/* EVA Chart Card */}
          <div className="app-card p-5 border-indigo-500/15 flex flex-col justify-between print:border-slate-800 print:shadow-none">
            <div>
              <div className="flex justify-between items-start mb-2">
                <h3 className="text-sm font-bold uppercase tracking-wider text-indigo-300">
                  Economic Value Added (EVA) Trend
                </h3>
                {evaData.length > 0 && (
                  <span className="badge-muted text-[10px]">
                    WACC: {fmtPct(evaData[0]?.wacc)}
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400 mb-4">
                Compares operational returns (NOPAT) against the monthly charge for Invested Capital. Amber line below zero points to economic wealth destruction.
              </p>
            </div>
            
            {evaData.length > 0 ? (
              <div className="h-[280px] w-full mt-2">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={evaData} margin={{ top: 10, right: 5, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis 
                      dataKey="period" 
                      tick={{ fill: '#64748b', fontSize: 9 }}
                    />
                    <YAxis tick={{ fill: '#64748b', fontSize: 10 }} />
                    <Tooltip
                      contentStyle={{ background: '#090d16', border: '1px solid #334155', borderRadius: 8 }}
                      labelStyle={{ color: '#94a3b8', fontWeight: 'bold' }}
                    />
                    <Legend wrapperStyle={{ fontSize: '10px', paddingTop: '10px' }} />
                    <Bar dataKey="nopat" name="NOPAT Proxy" fill="#10b981" fillOpacity={0.8} maxBarSize={16} />
                    <Area type="monotone" dataKey="capital_charge" name="Capital Charge" fill="#6366f1" fillOpacity={0.12} stroke="#6366f1" strokeWidth={1.5} />
                    <Line type="monotone" dataKey="eva" name="EVA (Net)" stroke="#fbbf24" strokeWidth={2.5} dot={{ r: 3, fill: '#fbbf24' }} />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="h-[280px] flex items-center justify-center text-slate-600 text-xs">
                No balance-sheet or WACC coordinates available. Ensure data_bilan and WACC configuration are applied.
              </div>
            )}
          </div>

          {/* VPMF Growth Decomposition Stacked Bar Chart */}
          <div className="app-card p-5 border-fuchsia-500/15 flex flex-col justify-between print:border-slate-800 print:shadow-none">
            <div>
              <h3 className="text-sm font-bold uppercase tracking-wider text-fuchsia-300 mb-2">
                Organic vs. Inflationary Growth Bridge (VPMF)
              </h3>
              <p className="text-xs text-slate-400 mb-4">
                Decomposes nominal monthly activity. The sky-blue stacked bar shows true volume growth, and the fuchsia bar captures pricing adjustments driven strictly by inflation.
              </p>
            </div>

            {vpmfData.length > 0 ? (
              <div className="h-[280px] w-full mt-2">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={vpmfData} margin={{ top: 10, right: 5, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis 
                      dataKey="period" 
                      tick={{ fill: '#64748b', fontSize: 9 }}
                    />
                    <YAxis tick={{ fill: '#64748b', fontSize: 10 }} />
                    <Tooltip
                      contentStyle={{ background: '#090d16', border: '1px solid #334155', borderRadius: 8 }}
                      labelStyle={{ color: '#94a3b8', fontWeight: 'bold' }}
                    />
                    <Legend wrapperStyle={{ fontSize: '10px', paddingTop: '10px' }} />
                    <Bar dataKey="price_effect" name="Price Effect (Inflation)" stackId="stack" fill="#d946ef" fillOpacity={0.7} maxBarSize={16} />
                    <Bar dataKey="volume_effect" name="Real Volume Growth" stackId="stack" fill="#0ea5e9" fillOpacity={0.8} maxBarSize={16} />
                    <Line type="monotone" dataKey="nominal" name="Nominal Total" stroke="#ffffff" strokeWidth={1.5} dot={false} />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="h-[280px] flex items-center justify-center text-slate-600 text-xs">
                No monthly timeseries deflators available. Double-check econ tables are configured.
              </div>
            )}
          </div>

        </div>

        {/* SECTION 3: TOP RANKED PERFORMANCE SUB-TABLES (SIDE-BY-SIDE OR STACKED) */}
        <div className="grid gap-6 md:grid-cols-2 print:grid-cols-2 print:gap-6">
          
          {/* Top Partners */}
          <div className="app-card p-4 border-slate-800 print:shadow-none">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3 border-b border-slate-800 pb-2">
              Top 5 Performing Partners (Turnover MAD)
            </h3>
            {topPartners.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="text-slate-500 border-b border-slate-800">
                      <th className="py-2 font-semibold">Partner</th>
                      <th className="py-2 font-semibold text-right">Nominal</th>
                      <th className="py-2 font-semibold text-right">Real (Base)</th>
                      <th className="py-2 font-semibold text-right text-red-400">Drift %</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/50">
                    {topPartners.map((row, idx) => {
                      const drift = row.nominal && row.real ? ((1 - (row.real / row.nominal)) * 100) : 0
                      return (
                        <tr key={idx} className="text-slate-300">
                          <td className="py-2 font-medium text-white">{row.value || 'Unknown'}</td>
                          <td className="py-2 text-right font-mono">{fmt(row.nominal)}</td>
                          <td className="py-2 text-right font-mono text-sky-300">{fmt(row.real)}</td>
                          <td className="py-2 text-right font-mono text-slate-400">
                            {drift > 0 ? `-${drift.toFixed(1)}%` : '0.0%'}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-xs text-slate-600 text-center py-4">No top partner breakdown computed.</p>
            )}
          </div>

          {/* Top Channels */}
          <div className="app-card p-4 border-slate-800 print:shadow-none">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3 border-b border-slate-800 pb-2">
              Top 5 Distribution Channels (Turnover MAD)
            </h3>
            {topChannels.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="text-slate-500 border-b border-slate-800">
                      <th className="py-2 font-semibold">Channel</th>
                      <th className="py-2 font-semibold text-right">Nominal</th>
                      <th className="py-2 font-semibold text-right">Real (Base)</th>
                      <th className="py-2 font-semibold text-right text-red-400">Drift %</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/50">
                    {topChannels.map((row, idx) => {
                      const drift = row.nominal && row.real ? ((1 - (row.real / row.nominal)) * 100) : 0
                      return (
                        <tr key={idx} className="text-slate-300">
                          <td className="py-2 font-medium text-white capitalize">{row.value || 'Unknown'}</td>
                          <td className="py-2 text-right font-mono">{fmt(row.nominal)}</td>
                          <td className="py-2 text-right font-mono text-sky-300">{fmt(row.real)}</td>
                          <td className="py-2 text-right font-mono text-slate-400">
                            {drift > 0 ? `-${drift.toFixed(1)}%` : '0.0%'}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-xs text-slate-600 text-center py-4">No top channel breakdown computed.</p>
            )}
          </div>

        </div>

        {/* SECTION 4: AI EXECUTIVE BRIEFING & EXECUTIVE NARRATIVE (MAIN ATTRACTION) */}
        <div className="app-card p-5 border-emerald-500/20 bg-emerald-950/5 print:bg-transparent print:border-slate-800 print:shadow-none">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between mb-4 print:hidden">
            <div>
              <h3 className="text-sm font-bold uppercase tracking-wider text-emerald-400 flex items-center gap-2">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
                </svg>
                AI-Generated Corporate Financial Commentary
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Dynamic, real-time context analysis powered by Google Gemini.
              </p>
            </div>
            <button 
              onClick={generateAiNarrative} 
              disabled={isGeneratingAi || !summary}
              className="btn-primary text-xs py-1.5 px-3 bg-emerald-700 hover:bg-emerald-600 flex items-center gap-1.5 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {isGeneratingAi ? (
                <>
                  <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  Generating Narrative...
                </>
              ) : (
                <>
                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/><path d="M16 16h5v5"/></svg>
                  Regenerate Analysis
                </>
              )}
            </button>
          </div>

          {/* AI Output (Markdown rendered beautifully) */}
          <div className="space-y-4">
            
            {/* Show error if AI request failed */}
            {aiError && (
              <div className="bg-red-950/20 border border-red-500/30 text-red-200 text-xs p-3 rounded-lg print:hidden">
                <strong>Narrative Automation Warning:</strong> {aiError}
              </div>
            )}

            {isGeneratingAi ? (
              <div className="py-12 flex flex-col items-center justify-center space-y-3 print:hidden">
                <div className="relative w-10 h-10">
                  <div className="absolute inset-0 rounded-full border-4 border-emerald-500/20 animate-ping"></div>
                  <div className="absolute inset-0 rounded-full border-4 border-t-emerald-500 border-r-transparent border-b-transparent border-l-transparent animate-spin"></div>
                </div>
                <p className="text-xs text-emerald-400 font-semibold tracking-wider uppercase animate-pulse">Running advanced macro evaluations...</p>
              </div>
            ) : aiNarrative ? (
              <div className="prose prose-invert prose-emerald max-w-none text-sm text-slate-300 leading-relaxed border-t border-slate-800/80 pt-4 print:border-none print:pt-0">
                {/* Print Title */}
                <h3 className="hidden print:block text-base font-bold text-emerald-400 uppercase tracking-wider mb-3">
                  Executive Briefing & Strategic Narrative
                </h3>
                <ReactMarkdown>{aiNarrative}</ReactMarkdown>
                
                {/* Editable Textbox Fallback / Direct Adjustments (Hidden on print) */}
                <div className="mt-6 pt-4 border-t border-slate-800/60 print:hidden">
                  <label className="text-xs text-slate-500 font-semibold uppercase tracking-wider block mb-1">
                    Direct Adjustments / Analysts Notes (Will sync with Printed Report)
                  </label>
                  <textarea 
                    value={aiNarrative}
                    onChange={(e) => setAiNarrative(e.target.value)}
                    rows={8}
                    className="app-input font-mono text-xs p-3 bg-slate-950/50"
                    placeholder="Enter manual financial commentary or overwrite AI brief here..."
                  />
                </div>
              </div>
            ) : (
              <div className="py-6 text-center text-xs text-slate-500 print:hidden">
                Click **Regenerate Analysis** to dynamically assemble AI analysis for {table}.
              </div>
            )}

          </div>
        </div>

      </div>

    </div>
  )
}
