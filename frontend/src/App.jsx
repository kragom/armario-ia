import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './contexts/AuthContext'
import Login from './pages/Login'
import Home from './pages/Home'
import Entry from './pages/Entry'
import Wardrobe from './pages/Wardrobe'
import ClothesDetail from './pages/ClothesDetail'
import Outfit from './pages/Outfit'
import Recommendation from './pages/Recommendation'
import TabBar from './components/TabBar'
import './index.css'

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="min-h-screen flex items-center justify-center"><div className="w-8 h-8 border-4 border-zinc-200 border-t-accent rounded-full animate-spin" /></div>
  if (!user) return <Navigate to="/login" replace />
  return children
}

function App() {
  const { user, loading } = useAuth()

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center">
      <div className="w-8 h-8 border-4 border-zinc-200 border-t-accent rounded-full animate-spin" />
    </div>
  }

  if (!user) {
    return (
      <Router>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </Router>
    )
  }

  return (
    <Router>
      <div className="min-h-screen bg-[var(--bg-primary)] text-[var(--text-primary)] pb-24 max-w-md mx-auto relative shadow-sm">
        <Routes>
          <Route path="/" element={<ProtectedRoute><Home /></ProtectedRoute>} />
          <Route path="/entry" element={<ProtectedRoute><Entry /></ProtectedRoute>} />
          <Route path="/wardrobe" element={<ProtectedRoute><Wardrobe /></ProtectedRoute>} />
          <Route path="/clothes/:id" element={<ProtectedRoute><ClothesDetail /></ProtectedRoute>} />
          <Route path="/outfit" element={<ProtectedRoute><Outfit /></ProtectedRoute>} />
          <Route path="/recommendation" element={<ProtectedRoute><Recommendation /></ProtectedRoute>} />
          <Route path="/login" element={<Navigate to="/" replace />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        <TabBar />
      </div>
    </Router>
  )
}

export default App
