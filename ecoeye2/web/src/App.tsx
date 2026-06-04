import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { AdjustmentsPage } from './pages/AdjustmentsPage'
import { DataPage } from './pages/DataPage'
import { ForecastPage } from './pages/ForecastPage'
import { IngestPage } from './pages/IngestPage'
import { InsightsPage } from './pages/InsightsPage'
import { ReportPage } from './pages/ReportPage'
import { SettingsPage } from './pages/SettingsPage'
import { VisualizePage } from './pages/VisualizePage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Navigate to="/insights" replace />} />
          <Route path="/insights" element={<InsightsPage />} />
          <Route path="/report" element={<ReportPage />} />
          <Route path="/ingest" element={<IngestPage />} />
          <Route path="/data" element={<DataPage />} />
          <Route path="/adjustments" element={<AdjustmentsPage />} />
          <Route path="/visualize" element={<VisualizePage />} />
          <Route path="/forecast" element={<ForecastPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/insights" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
