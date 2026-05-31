import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ArrowLeft, RefreshCw } from 'lucide-react'

import { API_BASE, toImageUrl, authFetch } from '../utils/api'

export default function ClothesDetail() {
    const { t } = useTranslation()
    const navigate = useNavigate()
    const { id } = useParams()
    const [item, setItem] = useState(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState('')
    const [analyzing, setAnalyzing] = useState(false)

    useEffect(() => {
        fetchClothesDetail()
    }, [id])

    const fetchClothesDetail = async () => {
        setLoading(true)
        setError('')
        try {
            const response = await authFetch(`${API_BASE}/clothes/${id}`)
            if (!response.ok) {
                throw new Error(response.status === 404 ? 'NOT_FOUND' : 'FETCH_FAILED')
            }
            const data = await response.json()
            setItem(data)
        } catch (err) {
            setItem(null)
            setError(err.message || 'FETCH_FAILED')
        } finally {
            setLoading(false)
        }
    }

    const handleRetryAnalysis = async () => {
        setAnalyzing(true)
        try {
            const res = await authFetch(`${API_BASE}/clothes/${id}/analyze`, { method: 'POST' })
            if (!res.ok) {
                const err = await res.json().catch(() => ({}))
                throw new Error(err.detail || 'Error al analizar')
            }
            setItem(await res.json())
        } catch (e) {
            setError(e.message)
        } finally {
            setAnalyzing(false)
        }
    }

    const isPending = item?.analysis_status === 'pending'

    const renderTags = (values) => {
        if (!Array.isArray(values) || values.length === 0) {
            return <span className="text-sm text-zinc-400">{t('clothesDetail.empty')}</span>
        }
        return (
            <div className="flex flex-wrap gap-2">
                {values.map(value => (
                    <span key={value} className="px-2 py-1 text-xs rounded-md bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-300">
                        {value}
                    </span>
                ))}
            </div>
        )
    }

    if (loading) {
        return (
            <div className="min-h-screen bg-[var(--bg-primary)] flex flex-col items-center justify-center">
                <div className="w-10 h-10 border-4 border-zinc-200 dark:border-zinc-700 border-t-accent rounded-full animate-spin"></div>
                <p className="mt-4 text-sm text-zinc-500">{t('clothesDetail.loading')}</p>
            </div>
        )
    }

    if (!item || error) {
        return (
            <div className="min-h-screen bg-[var(--bg-primary)] p-4">
                <header className="glass-header px-4 py-4 -mx-4">
                    <button className="btn-icon" onClick={() => navigate('/wardrobe')}>
                        <ArrowLeft size={22} />
                    </button>
                </header>
                <div className="mt-8 card p-6 text-center space-y-4">
                    <p className="text-sm text-zinc-500">
                        {error === 'NOT_FOUND' ? t('clothesDetail.notFound') : t('clothesDetail.loadFailed')}
                    </p>
                    <button className="btn-secondary mx-auto" onClick={fetchClothesDetail}>
                        <RefreshCw size={16} />
                        {t('clothesDetail.retry')}
                    </button>
                </div>
            </div>
        )
    }

    return (
        <div className="min-h-screen bg-[var(--bg-primary)] pb-8 animate-fade-in">
            <header className="glass-header px-4 py-4 sticky top-0">
                <div className="flex items-center gap-2">
                    <button className="btn-icon" onClick={() => navigate('/wardrobe')}>
                        <ArrowLeft size={22} />
                    </button>
                    <h1 className="text-xl font-serif font-semibold text-[var(--text-primary)]">{t('clothesDetail.title')}</h1>
                </div>
            </header>

            <div className="p-4 space-y-4">
                <article className="card overflow-hidden">
                    <div className="aspect-square bg-zinc-100 dark:bg-zinc-800 p-6 flex items-center justify-center">
                        <img
                            src={toImageUrl(item.image_url)}
                            alt={item.item}
                            className="w-full h-full object-contain drop-shadow-md"
                        />
                    </div>
                    <div className="p-4 border-t border-zinc-100 dark:border-zinc-800">
                        <div className="flex items-center gap-2">
                            <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">{item.item}</h2>
                            {isPending && (
                                <span className="text-[11px] px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-800 font-medium">
                                    Pendiente
                                </span>
                            )}
                        </div>
                        <p className="text-sm text-zinc-500 mt-1">{item.category}</p>
                    </div>
                </article>

                <section className="card p-4 space-y-4">
                    {isPending && (
                        <div className="flex gap-2">
                            <button
                                onClick={handleRetryAnalysis}
                                disabled={analyzing}
                                className="flex-1 py-2.5 rounded-lg bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 text-sm font-medium hover:opacity-90 disabled:opacity-50 transition-opacity cursor-pointer flex items-center justify-center gap-2"
                            >
                                {analyzing ? (
                                    <><span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> Analizando...</>
                                ) : (
                                    <><RefreshCw size={15} /> Re-analizar con IA</>
                                )}
                            </button>
                            <button
                                onClick={() => navigate(`/entry?edit=${item.id}`)}
                                className="px-4 py-2.5 rounded-lg border border-zinc-200 dark:border-zinc-700 text-sm font-medium text-zinc-700 dark:text-zinc-300 hover:bg-zinc-50 dark:hover:bg-zinc-800 transition-colors cursor-pointer"
                            >
                                Editar manual
                            </button>
                        </div>
                    )}

                    <div>
                        <h3 className="text-sm font-medium text-zinc-500">{t('clothesDetail.description')}</h3>
                        <p className="mt-1 text-sm text-zinc-800 dark:text-zinc-200">{item.description || t('clothesDetail.empty')}</p>
                    </div>

                    <div>
                        <h3 className="text-sm font-medium text-zinc-500">{t('clothesDetail.notes')}</h3>
                        <p className="mt-1 text-sm text-zinc-800 dark:text-zinc-200">{item.notes || t('clothesDetail.notesEmpty')}</p>
                    </div>

                    <div>
                        <h3 className="text-sm font-medium text-zinc-500">{t('clothesDetail.color')}</h3>
                        <p className="mt-1 text-sm text-zinc-800 dark:text-zinc-200">{item.color_semantics || t('clothesDetail.empty')}</p>
                    </div>

                    <div>
                        <h3 className="text-sm font-medium text-zinc-500">{t('clothesDetail.style')}</h3>
                        <div className="mt-1">{renderTags(item.style_semantics)}</div>
                    </div>

                    <div>
                        <h3 className="text-sm font-medium text-zinc-500">{t('clothesDetail.season')}</h3>
                        <div className="mt-1">{renderTags(item.season_semantics)}</div>
                    </div>

                    <div>
                        <h3 className="text-sm font-medium text-zinc-500">{t('clothesDetail.usage')}</h3>
                        <div className="mt-1">{renderTags(item.usage_semantics)}</div>
                    </div>
                </section>
            </div>
        </div>
    )
}
