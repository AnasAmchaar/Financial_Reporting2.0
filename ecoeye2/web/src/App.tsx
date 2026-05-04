import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { AdjustmentsPage } from './pages/AdjustmentsPage'
import { DataPage } from './pages/DataPage'
import { IngestPage } from './pages/IngestPage'
import { SettingsPage } from './pages/SettingsPage'
import { VisualizePage } from './pages/VisualizePage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<IngestPage />} />
          <Route path="/data" element={<DataPage />} />
          <Route path="/adjustments" element={<AdjustmentsPage />} />
          <Route path="/visualize" element={<VisualizePage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
