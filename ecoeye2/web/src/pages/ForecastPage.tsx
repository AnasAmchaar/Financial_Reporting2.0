import { useEffect, useState } from 'react'
import {
  Area,
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  BarChart,
} from 'recharts'
import ReactMarkdown from 'react-markdown'
import { apiFetch } from '../lib/api'

type HistoricalPoint = {
  period: string
  amount: number
  amount_real?: number
}

type PredictionPoint = {
  period: string
  predicted_nominal: number
  predicted_real: number
  confidence_lower: number
  confidence_upper: number
}

type FeatureImportance = {
  feature: string
  importance: number
}

type ForecastResponse = {
  historical: HistoricalPoint[]
  predictions: PredictionPoint[]
  metrics: Record<string, number>
  feature_importances: FeatureImportance[]
  model_info: Record<string, string>
}

type RagStatus = {
  status: string
  chunk_count: number
  last_indexed: string | null
  collection: string
}

function fmt(n: number | null | undefined) {
  if (n == null) return '—'
  return n.toLocaleString(undefined, { maximumFractionDigits: 0 })
}

export function ForecastPage() {
  const [table, setTable] = useState('data_reel')
  const [horizon, setHorizon] = useState(12)
  const [forecastData, setForecastData] = useState<ForecastResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [err, setErr] = useState('')

  // AI interpretation
  const [aiInterpretation, setAiInterpretation] = useState('')
  const [isGeneratingAi, setIsGeneratingAi] = useState(false)

  // RAG status
  const [ragStatus, setRagStatus] = useState<RagStatus | null>(null)
  const [isIndexing, setIsIndexing] = useState(false)

  // Fetch RAG status on mount
  useEffect(() => {
    apiFetch<RagStatus>('/api/v1/ai/rag/status')
      .then(setRagStatus)
      .catch(() => setRagStatus(null))
  }, [])

  const runForecast = async () => {
    setIsLoading(true)
    setErr('')
    setAiInterpretation('')

    try {
      const params = new URLSearchParams({
        table,
        horizon: String(horizon),
        group_by: 'overall',
      })
      const data = await apiFetch<ForecastResponse>(`/api/v1/forecast/predict?${params}`)
      setForecastData(data)

      // Auto-generate AI interpretation
      if (data.predictions.length > 0) {
        generateAiInterpretation(data)
      }
    } catch (e: any) {
      setErr(e.message || String(e))
    } finally {
      setIsLoading(false)
    }
  }

  const generateAiInterpretation = async (data: ForecastResponse) => {
    setIsGeneratingAi(true)
    try {
      const lastHistorical = data.historical.slice(-6)
      const predSummary = data.predictions.map(p => ({
        period: p.period,
        nominal: p.predicted_nominal,
        real: p.predicted_real,
        conf_range: `${p.confidence_lower} - ${p.confidence_upper}`,
      }))

      const prompt = `Analyze the following ML financial forecast results and provide an executive-level interpretation:

**Model Info:** ${JSON.stringify(data.model_info)}
**Model Performance:** R²=${data.metrics.r2?.toFixed(3)}, MAE=${fmt(data.metrics.mae)}, RMSE=${fmt(data.metrics.rmse)}
**Training Data:** ${data.metrics.n_train} monthly observations
**Forecast Horizon:** ${data.metrics.horizon} months

**Recent Historical Data (last 6 months):**
${JSON.stringify(lastHistorical, null, 2)}

**Predictions:**
${JSON.stringify(predSummary, null, 2)}

**Top Feature Importances:**
${JSON.stringify(data.feature_importances.slice(0, 6), null, 2)}

Provide:
1. **Forecast Outlook**: What direction are revenues heading? Is the trend positive or negative?
2. **Real vs. Nominal Gap**: Quantify the projected purchasing power erosion.
3. **Key Drivers**: Which features (CPI, PPI, seasonality, trend) are driving the forecast?
4. **Confidence Assessment**: How reliable are these predictions based on the metrics?
5. **Actionable Recommendations**: What should the business do based on these projections?

Be concise, data-driven, and use specific numbers from the forecast.`

      const res = await apiFetch<{ response: string }>('/api/v1/ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: prompt, use_rag: true }),
      })
      setAiInterpretation(res.response)
    } catch (e: any) {
      setAiInterpretation(`*Could not generate AI interpretation: ${e.message}*`)
    } finally {
      setIsGeneratingAi(false)
    }
  }

  const handleReindex = async () => {
    setIsIndexing(true)
    try {
      const result = await apiFetch<any>('/api/v1/ai/rag/reindex', { method: 'POST' })
      setRagStatus(prev => prev ? { ...prev, status: 'ready', chunk_count: result.chunks_indexed, last_indexed: new Date().toISOString() } : null)
    } catch (e: any) {
      console.error('Reindex failed:', e)
    } finally {
      setIsIndexing(false)
    }
  }

  // Expose page context for AI ChatBot
  useEffect(() => {
    window.__ECOEYE_CONTEXT__ = {
      page: 'AI Forecast',
      forecast: forecastData ? {
        metrics: forecastData.metrics,
        predictions_count: forecastData.predictions.length,
        model_info: forecastData.model_info,
      } : null,
      rag_status: ragStatus,
    }
  }, [forecastData, ragStatus])

  // Merge historical + predictions for the chart
  const chartData = forecastData
    ? [
        ...forecastData.historical.map(h => ({
          period: h.period,
          historical_nominal: h.amount,
          historical_real: h.amount_real ?? null,
          predicted_nominal: null as number | null,
          predicted_real: null as number | null,
          confidence_lower: null as number | null,
          confidence_upper: null as number | null,
        })),
        // Bridge point: last historical + first prediction
        ...(forecastData.predictions.length > 0
          ? [
              {
                period: forecastData.predictions[0].period,
                historical_nominal: null as number | null,
                historical_real: null as number | null,
                predicted_nominal: forecastData.predictions[0].predicted_nominal,
                predicted_real: forecastData.predictions[0].predicted_real,
                confidence_lower: forecastData.predictions[0].confidence_lower,
                confidence_upper: forecastData.predictions[0].confidence_upper,
              },
              ...forecastData.predictions.slice(1).map(p => ({
                period: p.period,
                historical_nominal: null as number | null,
                historical_real: null as number | null,
                predicted_nominal: p.predicted_nominal,
                predicted_real: p.predicted_real,
                confidence_lower: p.confidence_lower,
                confidence_upper: p.confidence_upper,
              })),
            ]
          : []),
      ]
    : []

  const featureLabels: Record<string, string> = {
    month_num: 'Month',
    year: 'Year',
    quarter: 'Quarter',
    trend: 'Trend',
    sin_month: 'Seasonality (sin)',
    cos_month: 'Seasonality (cos)',
    cpi: 'CPI',
    ppi: 'PPI',
    cpi_yoy: 'CPI YoY',
    policy_rate: 'Policy Rate',
  }

  return (
    <div className="mx-auto max-w-6xl space-y-8">
      {/* Header */}
      <div>
        <h1 className="section-title flex items-center gap-3">
          <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-violet-500/20 border border-violet-500/30">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-violet-400">
              <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
            </svg>
          </span>
          AI Forecast & Predictions
        </h1>
        <p className="section-subtitle mt-2 max-w-3xl">
          Machine learning predictions for future financial periods, powered by gradient boosting + exponential smoothing
          ensembled with CPI, PPI, and macroeconomic indicators. RAG-grounded AI interpretation.
        </p>
      </div>

      {/* Controls */}
      <div className="app-card p-5">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div className="flex flex-wrap items-end gap-4">
            <div>
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1.5">Dataset</label>
              <input
                value={table}
                onChange={e => setTable(e.target.value)}
                className="app-input max-w-[160px] px-3 py-2"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1.5">
                Horizon: <span className="text-violet-400 font-bold">{horizon} months</span>
              </label>
              <input
                type="range"
                min={3}
                max={36}
                step={3}
                value={horizon}
                onChange={e => setHorizon(Number(e.target.value))}
                className="w-48 accent-violet-500"
              />
              <div className="flex justify-between text-[10px] text-slate-600 w-48 mt-0.5">
                <span>3m</span><span>12m</span><span>24m</span><span>36m</span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* RAG Status Badge */}
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <div className={`w-2 h-2 rounded-full ${ragStatus?.status === 'ready' ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)]' : 'bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.6)]'}`} />
              <span>RAG: {ragStatus?.status === 'ready' ? `${ragStatus.chunk_count} chunks` : 'Not indexed'}</span>
              <button
                onClick={handleReindex}
                disabled={isIndexing}
                className="text-violet-400 hover:text-violet-300 underline underline-offset-2 disabled:opacity-50 disabled:no-underline"
              >
                {isIndexing ? 'Indexing…' : 'Re-index'}
              </button>
            </div>

            <button
              onClick={runForecast}
              disabled={isLoading}
              className="btn-primary flex items-center gap-2 px-5 py-2.5 font-semibold shadow-lg shadow-violet-500/20 bg-violet-600 hover:bg-violet-500 disabled:opacity-50"
            >
              {isLoading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Training Model…
                </>
              ) : (
                <>
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2"/>
                  </svg>
                  Generate Forecast
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {err && (
        <div className="app-card border-red-500/35 bg-red-950/30 p-4 text-sm text-red-200">
          <p className="font-semibold">Forecast Error</p>
          <p className="mt-1 font-mono text-xs text-red-100/90">{err}</p>
        </div>
      )}

      {/* Forecast Chart */}
      {forecastData && chartData.length > 0 && (
        <div className="app-card p-5 border-violet-500/15">
          <div className="flex justify-between items-start mb-4">
            <div>
              <h2 className="text-sm font-bold uppercase tracking-wider text-violet-300">
                Revenue Forecast: Historical & Predicted
              </h2>
              <p className="text-xs text-slate-400 mt-1">
                Solid lines = actual data • Dashed lines = ML predictions • Shaded band = 80% confidence interval
              </p>
            </div>
            <span className="badge-muted text-[10px]">
              {forecastData.model_info.ensemble || 'Ensemble'}
            </span>
          </div>

          <div className="h-[380px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chartData} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
                <defs>
                  <linearGradient id="histGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="confGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.15} />
                    <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0.03} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis
                  dataKey="period"
                  tick={{ fill: '#64748b', fontSize: 9 }}
                  interval="preserveStartEnd"
                />
                <YAxis tick={{ fill: '#64748b', fontSize: 10 }} />
                <Tooltip
                  contentStyle={{ background: '#090d16', border: '1px solid #334155', borderRadius: 8, fontSize: 12 }}
                  labelStyle={{ color: '#94a3b8', fontWeight: 'bold' }}
                  formatter={(value: number, name: string) => [value ? fmt(value) + ' MAD' : '—', name]}
                />
                <Legend wrapperStyle={{ fontSize: '10px', paddingTop: '10px' }} />

                {/* Confidence band */}
                <Area
                  type="monotone"
                  dataKey="confidence_upper"
                  fill="url(#confGradient)"
                  stroke="none"
                  name="Confidence Upper"
                  legendType="none"
                />
                <Area
                  type="monotone"
                  dataKey="confidence_lower"
                  fill="#090d16"
                  stroke="none"
                  name="Confidence Lower"
                  legendType="none"
                />

                {/* Historical */}
                <Area
                  type="monotone"
                  dataKey="historical_nominal"
                  fill="url(#histGradient)"
                  stroke="#10b981"
                  strokeWidth={2}
                  name="Historical Nominal"
                  dot={{ r: 2, fill: '#10b981' }}
                  connectNulls={false}
                />
                <Line
                  type="monotone"
                  dataKey="historical_real"
                  stroke="#0ea5e9"
                  strokeWidth={1.5}
                  name="Historical Real"
                  dot={{ r: 1.5, fill: '#0ea5e9' }}
                  connectNulls={false}
                />

                {/* Predicted */}
                <Line
                  type="monotone"
                  dataKey="predicted_nominal"
                  stroke="#a78bfa"
                  strokeWidth={2.5}
                  strokeDasharray="8 4"
                  name="Predicted Nominal"
                  dot={{ r: 3, fill: '#a78bfa', stroke: '#7c3aed', strokeWidth: 1 }}
                  connectNulls={false}
                />
                <Line
                  type="monotone"
                  dataKey="predicted_real"
                  stroke="#38bdf8"
                  strokeWidth={1.5}
                  strokeDasharray="5 3"
                  name="Predicted Real"
                  dot={{ r: 2, fill: '#38bdf8' }}
                  connectNulls={false}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Model Metrics + Feature Importance */}
      {forecastData && (
        <div className="grid gap-6 md:grid-cols-2">
          {/* Model Performance */}
          <div className="app-card p-5 border-slate-800">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-4 border-b border-slate-800 pb-2">
              Model Performance (Cross-Validated)
            </h3>
            <div className="grid grid-cols-3 gap-4">
              <div className="text-center">
                <div className="text-2xl font-black text-violet-300">
                  {forecastData.metrics.r2 != null ? forecastData.metrics.r2.toFixed(3) : '—'}
                </div>
                <div className="text-[10px] text-slate-500 uppercase tracking-wider mt-1">R² Score</div>
                <div className="mt-2 h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{
                      width: `${Math.max(0, Math.min(100, (forecastData.metrics.r2 ?? 0) * 100))}%`,
                      background: (forecastData.metrics.r2 ?? 0) > 0.7 ? '#10b981' : (forecastData.metrics.r2 ?? 0) > 0.4 ? '#f59e0b' : '#ef4444',
                    }}
                  />
                </div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-black text-sky-300">
                  {fmt(forecastData.metrics.mae)}
                </div>
                <div className="text-[10px] text-slate-500 uppercase tracking-wider mt-1">MAE (MAD)</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-black text-amber-300">
                  {fmt(forecastData.metrics.rmse)}
                </div>
                <div className="text-[10px] text-slate-500 uppercase tracking-wider mt-1">RMSE (MAD)</div>
              </div>
            </div>

            <div className="mt-5 pt-4 border-t border-slate-800/60">
              <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-2">Model Architecture</div>
              <div className="space-y-1.5 text-xs text-slate-400">
                {Object.entries(forecastData.model_info).map(([k, v]) => (
                  <div key={k} className="flex justify-between">
                    <span className="text-slate-500 capitalize">{k.replace(/_/g, ' ')}</span>
                    <span className="text-slate-300 font-mono text-[11px] text-right max-w-[60%] truncate">{v}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="mt-4 text-[10px] text-slate-600">
              Training samples: {forecastData.metrics.n_train} • Forecast horizon: {forecastData.metrics.horizon} months
            </div>
          </div>

          {/* Feature Importance */}
          <div className="app-card p-5 border-slate-800">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-4 border-b border-slate-800 pb-2">
              Feature Importance — What Drives the Forecast
            </h3>
            {forecastData.feature_importances.length > 0 ? (
              <div className="h-[250px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={forecastData.feature_importances.map(f => ({
                      ...f,
                      label: featureLabels[f.feature] || f.feature,
                      pct: Math.round(f.importance * 100),
                    }))}
                    layout="vertical"
                    margin={{ top: 0, right: 20, left: 0, bottom: 0 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
                    <XAxis type="number" tick={{ fill: '#64748b', fontSize: 10 }} domain={[0, 'auto']} />
                    <YAxis
                      type="category"
                      dataKey="label"
                      tick={{ fill: '#94a3b8', fontSize: 10 }}
                      width={110}
                    />
                    <Tooltip
                      contentStyle={{ background: '#090d16', border: '1px solid #334155', borderRadius: 8, fontSize: 12 }}
                      formatter={(value: number) => [`${(value * 100).toFixed(1)}%`, 'Importance']}
                    />
                    <Bar dataKey="importance" fill="#8b5cf6" fillOpacity={0.8} maxBarSize={20} radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="flex items-center justify-center h-[250px] text-slate-600 text-xs">
                No feature importance data available
              </div>
            )}
            <p className="mt-3 text-[10px] text-slate-500 border-t border-slate-800/60 pt-3">
              Shows which input variables most influence the model's predictions.
              Higher importance means the model relies more on that feature for accuracy.
            </p>
          </div>
        </div>
      )}

      {/* Prediction Table */}
      {forecastData && forecastData.predictions.length > 0 && (
        <div className="app-card p-5 border-slate-800">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3 border-b border-slate-800 pb-2">
            Detailed Forecast — Predicted Monthly Values
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="text-slate-500 border-b border-slate-800">
                  <th className="py-2 font-semibold">Period</th>
                  <th className="py-2 font-semibold text-right">Predicted Nominal (MAD)</th>
                  <th className="py-2 font-semibold text-right">Predicted Real (MAD)</th>
                  <th className="py-2 font-semibold text-right text-violet-400/70">Conf. Lower</th>
                  <th className="py-2 font-semibold text-right text-violet-400/70">Conf. Upper</th>
                  <th className="py-2 font-semibold text-right text-red-400/70">Erosion %</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50">
                {forecastData.predictions.map((p, idx) => {
                  const erosion = p.predicted_nominal > 0
                    ? ((1 - p.predicted_real / p.predicted_nominal) * 100)
                    : 0
                  return (
                    <tr key={idx} className="text-slate-300 hover:bg-slate-800/30 transition-colors">
                      <td className="py-2 font-medium text-white font-mono">{p.period}</td>
                      <td className="py-2 text-right font-mono text-emerald-300">{fmt(p.predicted_nominal)}</td>
                      <td className="py-2 text-right font-mono text-sky-300">{fmt(p.predicted_real)}</td>
                      <td className="py-2 text-right font-mono text-slate-500">{fmt(p.confidence_lower)}</td>
                      <td className="py-2 text-right font-mono text-slate-500">{fmt(p.confidence_upper)}</td>
                      <td className="py-2 text-right font-mono text-slate-400">
                        {erosion > 0 ? `-${erosion.toFixed(1)}%` : `${erosion.toFixed(1)}%`}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* AI Interpretation */}
      {forecastData && (
        <div className="app-card p-5 border-violet-500/20 bg-violet-950/5">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold uppercase tracking-wider text-violet-400 flex items-center gap-2">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
                </svg>
                AI Forecast Interpretation
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                RAG-grounded analysis powered by Gemini • Financial data context injected
              </p>
            </div>
            <button
              onClick={() => forecastData && generateAiInterpretation(forecastData)}
              disabled={isGeneratingAi}
              className="btn-secondary text-xs py-1.5 px-3 flex items-center gap-1.5 disabled:opacity-40"
            >
              {isGeneratingAi ? (
                <>
                  <div className="w-3.5 h-3.5 border-2 border-violet-400 border-t-transparent rounded-full animate-spin" />
                  Analyzing…
                </>
              ) : (
                <>
                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/><path d="M16 16h5v5"/></svg>
                  Regenerate
                </>
              )}
            </button>
          </div>

          {isGeneratingAi ? (
            <div className="py-12 flex flex-col items-center justify-center space-y-3">
              <div className="relative w-10 h-10">
                <div className="absolute inset-0 rounded-full border-4 border-violet-500/20 animate-ping" />
                <div className="absolute inset-0 rounded-full border-4 border-t-violet-500 border-r-transparent border-b-transparent border-l-transparent animate-spin" />
              </div>
              <p className="text-xs text-violet-400 font-semibold tracking-wider uppercase animate-pulse">
                Interpreting forecast with RAG context…
              </p>
            </div>
          ) : aiInterpretation ? (
            <div className="prose prose-invert prose-violet max-w-none text-sm text-slate-300 leading-relaxed border-t border-slate-800/80 pt-4">
              <ReactMarkdown>{aiInterpretation}</ReactMarkdown>
            </div>
          ) : (
            <div className="py-6 text-center text-xs text-slate-500">
              AI interpretation will appear here after the forecast is generated.
            </div>
          )}
        </div>
      )}

      {/* Empty state */}
      {!forecastData && !isLoading && !err && (
        <div className="app-card p-12 text-center space-y-4">
          <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-violet-500/10 border border-violet-500/20 mx-auto">
            <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-violet-400">
              <path d="M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2"/>
            </svg>
          </div>
          <div>
            <h3 className="text-lg font-semibold text-slate-200">Ready to Forecast</h3>
            <p className="text-sm text-slate-500 mt-1 max-w-md mx-auto">
              Select your dataset and forecast horizon, then click <strong className="text-violet-400">Generate Forecast</strong> to
              train the ML model and predict future financial values enriched with CPI, PPI, and macroeconomic features.
            </p>
          </div>
          <div className="text-xs text-slate-600 space-y-1">
            <p>📊 Gradient Boosting + Holt-Winters ensemble</p>
            <p>🔗 RAG-grounded AI interpretation</p>
            <p>📈 Confidence intervals via quantile regression</p>
          </div>
        </div>
      )}
    </div>
  )
}
