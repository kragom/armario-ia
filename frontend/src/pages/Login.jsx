import { useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useTranslation } from 'react-i18next'

export default function Login() {
  const { t } = useTranslation()
  const { login } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!username.trim() || !password.trim()) return
    setLoading(true)
    setError('')
    try {
      await login(username.trim().toLowerCase(), password)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[var(--bg-primary)] flex items-center justify-center p-6">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="text-4xl mb-2">👕</div>
          <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">Armario IA</h1>
          <p className="text-sm text-zinc-500 mt-1">Inicia sesión para continuar</p>
        </div>

        <form onSubmit={handleSubmit} className="card p-5 space-y-4">
          <div>
            <label className="text-xs font-medium text-zinc-600 dark:text-zinc-400 block mb-1.5">Usuario</label>
            <input
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              placeholder="naomi o hector"
              className="w-full px-3 py-2.5 rounded-lg border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-sm text-zinc-900 dark:text-zinc-100 placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-accent/30"
              autoFocus
            />
          </div>

          <div>
            <label className="text-xs font-medium text-zinc-600 dark:text-zinc-400 block mb-1.5">Contraseña</label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="Tu contraseña"
              className="w-full px-3 py-2.5 rounded-lg border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-sm text-zinc-900 dark:text-zinc-100 placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-accent/30"
            />
          </div>

          {error && (
            <p className="text-xs text-red-500 bg-red-50 dark:bg-red-900/20 px-3 py-2 rounded-lg">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading || !username.trim() || !password.trim()}
            className="w-full py-2.5 rounded-lg bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 text-sm font-medium hover:opacity-90 disabled:opacity-50 transition-opacity cursor-pointer"
          >
            {loading ? 'Entrando...' : 'Entrar'}
          </button>

          <p className="text-[11px] text-zinc-400 text-center">
            Primera vez? solo escribe tu usuario y una contraseña nueva
          </p>
        </form>
      </div>
    </div>
  )
}