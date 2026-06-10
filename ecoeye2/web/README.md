# EcoEye2 Frontend Web Application

This folder contains the React + TypeScript + Vite web client for the **EcoEye2** financial ETL and economic adjustment platform.

## 🚀 Tech Stack

- **React 19** with TypeScript
- **Vite 8** for lightning-fast HMR and bundling
- **Recharts** for interactive dashboards (nominal vs real, cross-validation evaluation diagnostics, EVA, and VPMF)
- **TailwindCSS** for UI styling
- **React Router 6** for routing

---

## 🛠️ Development Setup

Ensure you have [Node.js](https://nodejs.org/) (v18+) installed.

### 1. Install Dependencies
```bash
npm install
```

### 2. Start Dev Server
```bash
npm run dev
```
- App runs at: [http://localhost:5173](http://localhost:5173)
- API requests under `/api/v1/*` are proxied to the backend FastAPI server running at `http://localhost:8000`.

### 3. Production Build
```bash
npm run build
```
The build command compiles the React SPA and outputs static assets directly into the FastAPI backend static directory (`../server/static/`). This allows FastAPI to serve both the API and the SPA from a single port in production.

---

## 📁 Key Directories & Pages

- **`/src/pages/`**:
  - `InsightsPage.tsx`: Main dashboard showcasing macro summaries, data quality, and BAM key rate summaries.
  - `IngestPage.tsx`: File upload interface and raw pipeline extraction executions.
  - `DataPage.tsx`: Interactive SQLite table editor with full search, sorting, and manual row updates.
  - `AdjustmentsPage.tsx`: Macro indicator fetching controls and real-value deflation commands.
  - `VisualizePage.tsx`: Customizable multi-axis charting engine for nominal vs real data comparison.
  - `ForecastPage.tsx`: ML forecasting page ensembling Gradient Boosting + Holt-Winters with a comprehensive Model Evaluation and diagnostics tab.
  - `ReportPage.tsx`: Printable Automated Executive Report with EVA and VPMF charts.
  - `SettingsPage.tsx`: Active AI provider switching (Google GenAI vs Groq).
- **`/src/components/`**: Layout panels, custom table models, and the `ChatBot.tsx` floating assistant.
- **`/src/lib/`**: Unified fetch client utilities.
