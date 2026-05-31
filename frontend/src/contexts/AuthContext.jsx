import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { API_BASE } from '../utils/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  const getToken = () => localStorage.getItem('auth_token')

  useEffect(() => {
    const token = getToken()
    if (!token) {
      setLoading(false)
      return
    }
    fetch(`${API_BASE}/auth/check`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(r => {
        if (!r.ok) {
          localStorage.removeItem('auth_token')
          return null
        }
        return r.json()
      })
      .then(u => setUser(u))
      .catch(() => localStorage.removeItem('auth_token'))
      .finally(() => setLoading(false))
  }, [])

  const login = useCallback(async (username, password) => {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'Error al iniciar sesión')
    }
    const data = await res.json()
    localStorage.setItem('auth_token', data.token)
    setUser({ user_id: data.user_id, username: data.username, display_name: data.display_name })
    return data
  }, [])

  const logout = useCallback(async () => {
    const token = getToken()
    if (token) {
      await fetch(`${API_BASE}/auth/logout`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      }).catch(() => {})
    }
    localStorage.removeItem('auth_token')
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, getToken }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}