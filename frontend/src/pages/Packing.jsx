import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Luggage, Sun, CloudSun, Shirt, ArrowLeft, RefreshCw } from 'lucide-react'
import { API_BASE, toImageUrl, authFetch } from '../utils/api'

const WEATHER_ICONS = {
  sun: <Sun size={14} className="text-amber-500" />,
  cloud: <CloudSun size={14} className="text-zinc-500" />,
}

export default function Packing() {
  const { t } = useTranslation()
  const [days, setDays] = useState(3)
  const [location, setLocation] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [expandedDay, setExpandedDay] = useState(null)

  const generate = async () => {
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const params = new URLSearchParams({ days: String(days) })
      if (location.trim()) params.set('location', location.trim())

      const res = await authFetch(`${API_BASE}/maleta?${params}`)
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || 'Error al generar la maleta')
      }
      setResult(await res.json())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const totalItems = result?.total_items ?? 0

  return (
    <div className="px-4 pt-6 pb-6 space-y-5">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-400 to-rose-500 flex items-center justify-center">
          <Luggage size={20} className="text-white" />
        </div>
        <div>
          <h1 className="text-lg font-bold text-zinc-900 dark:text-zinc-100">Prepara la maleta</h1>
          <p className="text-xs text-zinc-500">Selecciona outfits para cada día del viaje</p>
        </div>
      </div>

      {!result && (
        <div className="card p-5 space-y-4">
          <div>
            <label className="text-xs font-medium text-zinc-600 dark:text-zinc-400 block mb-1.5">Días de viaje</label>
            <div className="flex items-center gap-3">
              <input
                type="range"
                min={1}
                max={14}
                value={days}
                onChange={e => setDays(Number(e.target.value))}
                className="flex-1 accent-zinc-900 dark:accent-zinc-100"
              />
              <span className="text-lg font-bold text-zinc-900 dark:text-zinc-100 min-w-[2rem] text-center">{days}</span>
            </div>
          </div>

          <div>
            <label className="text-xs font-medium text-zinc-600 dark:text-zinc-400 block mb-1.5">Destino (opcional)</label>
            <input
              type="text"
              value={location}
              onChange={e => setLocation(e.target.value)}
              placeholder="Ej: Madrid, Barcelona, París..."
              className="w-full px-3 py-2.5 rounded-lg border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-sm text-zinc-900 dark:text-zinc-100 placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-accent/30"
            />
          </div>

          {error && (
            <p className="text-xs text-red-500 bg-red-50 dark:bg-red-900/20 px-3 py-2 rounded-lg">{error}</p>
          )}

          <button
            onClick={generate}
            disabled={loading}
            className="w-full py-3 rounded-xl bg-gradient-to-r from-amber-500 to-rose-500 text-white font-medium text-sm hover:opacity-90 disabled:opacity-50 transition-opacity cursor-pointer flex items-center justify-center gap-2"
          >
            {loading ? (
              <><span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> Generando...</>
            ) : (
              <><Luggage size={16} /> Generar maleta</>
            )}
          </button>
        </div>
      )}

      {result && (
        <>
          <div className="card p-4 space-y-2">
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1">
                <p className="text-sm text-zinc-700 dark:text-zinc-300 leading-relaxed">{result.trip_summary}</p>
                <div className="flex gap-3 mt-2 text-xs text-zinc-500">
                  <span>{days} días</span>
                  <span>{totalItems} prendas</span>
                </div>
                {result.items_not_to_forget?.length > 0 && (
                  <div className="mt-2">
                    <p className="text-[11px] font-medium text-zinc-500 mb-1">No olvides:</p>
                    <div className="flex flex-wrap gap-1.5">
                      {result.items_not_to_forget.map((item, i) => (
                        <span key={i} className="text-[11px] px-2 py-0.5 rounded-full bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-800">
                          {item}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
              <div className="flex gap-1.5 shrink-0">
                <button
                  onClick={generate}
                  disabled={loading}
                  className="w-9 h-9 rounded-lg border border-zinc-200 dark:border-zinc-700 flex items-center justify-center text-zinc-500 hover:text-accent transition-colors cursor-pointer"
                  title="Regenerar"
                >
                  <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
                </button>
              </div>
            </div>
          </div>

          <div className="space-y-3">
            {result.days?.map((day) => (
              <button
                key={day.day}
                onClick={() => setExpandedDay(expandedDay === day.day ? null : day.day)}
                className="w-full card p-4 text-left cursor-pointer hover:shadow-md transition-shadow"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <div className="w-7 h-7 rounded-lg bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center text-xs font-bold text-zinc-600 dark:text-zinc-400">
                      {day.day}
                    </div>
                    <span className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">Día {day.day}</span>
                    <span className="text-[11px] text-zinc-400">{day.date}</span>
                  </div>
                  <span className="text-[11px] text-zinc-500 flex items-center gap-1">
                    {WEATHER_ICONS.sun} {day.weather_forecast?.split(',')[0] || ''}
                  </span>
                </div>

                <div className="flex items-center gap-3 text-xs mt-2">
                  {day.top && (
                    <div className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400">
                      <Shirt size={12} /> {day.top.name}
                    </div>
                  )}
                  {day.bottom && (
                    <div className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400">
                      <Shirt size={12} /> {day.bottom.name}
                    </div>
                  )}
                  {day.shoes && (
                    <div className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-purple-50 dark:bg-purple-900/20 text-purple-700 dark:text-purple-400">
                      <Shirt size={12} /> {day.shoes.name}
                    </div>
                  )}
                  {day.outerwear && (
                    <div className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-rose-50 dark:bg-rose-900/20 text-rose-700 dark:text-rose-400">
                      <Shirt size={12} /> {day.outerwear.name}
                    </div>
                  )}
                </div>

                {expandedDay === day.day && day.accessories?.length > 0 && (
                  <div className="mt-2 pt-2 border-t border-zinc-100 dark:border-zinc-800">
                    <p className="text-[11px] text-zinc-500 mb-1">Accesorios:</p>
                    <div className="flex flex-wrap gap-1.5">
                      {day.accessories.map((acc, i) => (
                        <span key={i} className="text-[11px] px-2 py-0.5 rounded-full bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400">
                          {acc.name}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
