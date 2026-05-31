import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './i18n'
import './index.css'
import App from './App.jsx'
import { ThemeProvider } from './contexts/ThemeContext.jsx'
import { UploadProvider } from './contexts/UploadContext.jsx'
import { RecommendationProvider } from './contexts/RecommendationContext.jsx'
import { AuthProvider } from './contexts/AuthContext.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <AuthProvider>
      <ThemeProvider>
        <UploadProvider>
          <RecommendationProvider>
            <App />
          </RecommendationProvider>
        </UploadProvider>
      </ThemeProvider>
    </AuthProvider>
  </StrictMode>,
)
