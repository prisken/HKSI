import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AppNav } from './components/AppNav'
import { HomePage } from './pages/HomePage'
import { PracticePage } from './pages/PracticePage'
import { ExamPage } from './pages/ExamPage'
import { ManualHomePage } from './pages/ManualHomePage'
import { ManualChapterPage } from './pages/ManualChapterPage'
import { ManualExtraPage } from './pages/ManualExtraPage'
import './App.css'

export default function App() {
  return (
    <BrowserRouter>
      <AppNav />
      <div className="app-shell">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/practice" element={<PracticePage />} />
          <Route path="/exam" element={<ExamPage />} />
          <Route path="/manual" element={<ManualHomePage />} />
          <Route path="/manual/extra/:extraId" element={<ManualExtraPage />} />
          <Route path="/manual/:chapterId" element={<ManualChapterPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}
