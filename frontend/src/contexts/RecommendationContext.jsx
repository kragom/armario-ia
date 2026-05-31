import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { API_BASE } from '../utils/api'
const DEFAULT_LOCATION = '上海, 上海市, 中国'

const RecommendationContext = createContext(null)

const INITIAL_STATE = {
  loading: false,
  error: '',
  weather: null,
  horoscope: null,
  temperatureRule: null,
  recommendation: '',
  outfitSummary: '',
  selectionReasons: {},
  suggestedTop: null,
  suggestedBottom: null,
  suggestedShoes: null,
  suggestedAccessories: [],
  purchaseSuggestions: [],
  goalRaw: '',
  goalNormalized: '',
  selectedCity: {
    name: DEFAULT_LOCATION,
    id: DEFAULT_LOCATION
  }
}

export function RecommendationProvider({ children }) {
  const [state, setState] = useState(INITIAL_STATE)
  const requestIdRef = useRef(0)

  useEffect(() => {
    const fetchDefaultCity = async () => {
      try {
        const response = await fetch(`${API_BASE}/config`)
        if (!response.ok) {
          return
        }

        const data = await response.json()
        const location = (data.weather_location || '').trim()
        if (!location) {
          return
        }

        setState(prev => ({
          ...prev,
          selectedCity: {
            name: location,
            id: location
          }
        }))
      } catch (error) {
        console.error('Failed to fetch default city config:', error)
      }
    }

    void fetchDefaultCity()
  }, [])

  const fetchRecommendation = useCallback(async (location, preferredName = null, goal = '') => {
    if (!location) {
      return null
    }

    const requestId = requestIdRef.current + 1
    requestIdRef.current = requestId
    setState(prev => ({ ...prev, loading: true, error: '' }))

    try {
      const params = new URLSearchParams({ location })
      const trimmedGoal = (goal || '').trim()
      if (trimmedGoal) {
        params.set('goal', trimmedGoal)
      }
      const response = await fetch(`${API_BASE}/recommendation?${params.toString()}`)
      if (!response.ok) {
        const errorPayload = await response.json().catch(() => ({}))
        if (requestId === requestIdRef.current) {
          setState(prev => ({
            ...prev,
            loading: false,
            error: errorPayload.detail || 'Failed to fetch recommendation'
          }))
        }
        return null
      }

      const data = await response.json()
      if (requestId !== requestIdRef.current) {
        return null
      }

      setState(prev => ({
        ...prev,
        loading: false,
        error: '',
        weather: data.weather || null,
        horoscope: data.horoscope || null,
        temperatureRule: data.temperature_rule || null,
        recommendation: data.recommendation_text || '',
        outfitSummary: data.outfit_summary || '',
        selectionReasons: data.selection_reasons || {},
        suggestedTop: data.suggested_top || null,
        suggestedBottom: data.suggested_bottom || null,
        suggestedShoes: data.suggested_shoes || null,
        suggestedAccessories: data.suggested_accessories || [],
        purchaseSuggestions: data.purchase_suggestions || [],
        goalRaw: data.goal_raw || '',
        goalNormalized: data.goal_normalized || '',
        selectedCity: preferredName
          ? { name: preferredName, id: location }
          : (data.weather?.location ? { name: data.weather.location, id: location } : prev.selectedCity)
      }))

      return data
    } catch (error) {
      if (requestId === requestIdRef.current) {
        setState(prev => ({
          ...prev,
          loading: false,
          error: error?.message || 'Failed to fetch recommendation'
        }))
      }
      return null
    }
  }, [])

  const value = useMemo(() => ({
    ...state,
    fetchRecommendation
  }), [state, fetchRecommendation])

  return (
    <RecommendationContext.Provider value={value}>
      {children}
    </RecommendationContext.Provider>
  )
}

export function useRecommendation() {
  const context = useContext(RecommendationContext)
  if (!context) {
    throw new Error('useRecommendation must be used within RecommendationProvider')
  }
  return context
}

