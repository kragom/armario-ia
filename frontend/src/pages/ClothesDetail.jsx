import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ArrowLeft, RefreshCw, Edit3, Check, X } from 'lucide-react'
import SelectableChips from '../components/SelectableChips'

import { API_BASE, toImageUrl, authFetch } from '../utils/api'

export default function ClothesDetail() {
    const { t } = useTranslation()
    const navigate = useNavigate()
    const { id } = useParams()
    const [item, setItem] = useState(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState('')
    const [analyzing, setAnalyzing] = useState(false)
    const [editing, setEditing] = useState(false)
    const [saving, setSaving] = useState(false)
    const [options, setOptions] = useState({ styles: [], seasons: [], usages: [], colors: [] })
    const [editData, setEditData] = useState({})

    useEffect(() => {
        fetchClothesDetail()
        authFetch(`${API_BASE}/wardrobe/options`).then(r => r.ok && r.json()).then(d => {
            if (d) setOptions(d)
        }).catch(() => {})
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

    const startEdit = () => {
        if (!item) return
        setEditData({
            style_semantics: [...(item.style_semantics || [])],
            season_semantics: [...(item.season_semantics || [])],
            usage_semantics: [...(item.usage_semantics || [])],
            color_semantics: item.color_semantics || '',
            description: item.description || '',
            notes: item.notes || '',
        })
        setEditing(true)
    }

    const cancelEdit = () => {
        setEditing(false)
        setEditData({})
    }

    const saveInline = async () => {
        setSaving(true)
        try {
            const payload = {
                category: item.category,
                item: item.item,
                description: item.description || '',
                image_filename: item.image_url.split('/').pop(),
                ...editData,
            }
            const res = await authFetch(`${API_BASE}/clothes/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            })
            if (res.ok) {
                setItem(await res.json())
                setEditing(false)
                setEditData({})
            } else {
                throw new Error('Save failed')
            }
        } catch (e) {
            console.error('Inline save error:', e)
        } finally {
            setSaving(false)
        }
    }

    const isPending = item?.analysis_status === 'pending'

    const renderTags = (values, field) => {
        const isEmpty = !Array.isArray(values) || values.length === 0
        if (editing && field) {
            const chips = field === 'color_semantics'
                ? <SelectableChips
                    options={options.colors}
                    selected={editData.color_semantics}
                    onChange={(v) => setEditData(prev => ({ ...prev, color_semantics: v }))}
                    type="color"
                    colorChips
                  />
                : <SelectableChips
                    options={options[field.replace('_semantics', 's')] || []}
                    selected={editData[field] || []}
                    onChange={(v) => setEditData(prev => ({ ...prev, [field]: v }))}
                  />
            return <div className="mt-1">{chips}</div>
        }
        if (isEmpty) {
            return <span className="text-sm text-zinc-400">{t('clothesDetail.empty')}</span>
        }
        return (
            <div className="flex flex-wrap gap-2 mt-1">
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
                    {isPending && !editing && (
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

                    <div className="flex items-center justify-between">
                        <h3 className="text-sm font-medium text-zinc-500">{t('clothesDetail.description')}</h3>
                        {!editing && (
                            <button onClick={startEdit} className="text-xs text-accent hover:underline flex items-center gap-1 cursor-pointer">
                                <Edit3 size={12} /> {t('clothesDetail.editQuick')}
                            </button>
                        )}
                    </div>
                    {editing ? (
                        <textarea
                            value={editData.description ?? item.description}
                            onChange={(e) => setEditData(prev => ({ ...prev, description: e.target.value }))}
                            rows={2}
                            className="input-field resize-none text-sm"
                            placeholder={t('entry.descriptionPlaceholder')}
                        />
                    ) : (
                        <p className="mt-1 text-sm text-zinc-800 dark:text-zinc-200">{item.description || t('clothesDetail.empty')}</p>
                    )}

                    <div>
                        <h3 className="text-sm font-medium text-zinc-500">{t('clothesDetail.notes')}</h3>
                        {editing ? (
                            <textarea
                                value={editData.notes}
                                onChange={(e) => setEditData(prev => ({ ...prev, notes: e.target.value }))}
                                rows={2}
                                className="input-field resize-none mt-1 text-sm"
                                placeholder={t('entry.notesPlaceholder')}
                            />
                        ) : (
                            <p className="mt-1 text-sm text-zinc-800 dark:text-zinc-200">{item.notes || t('clothesDetail.notesEmpty')}</p>
                        )}
                    </div>

                    <div>
                        <h3 className="text-sm font-medium text-zinc-500">{t('clothesDetail.color')}</h3>
                        {renderTags(editing ? null : item.color_semantics ? [item.color_semantics] : [], editing ? 'color_semantics' : null)}
                    </div>

                    <div>
                        <h3 className="text-sm font-medium text-zinc-500">{t('clothesDetail.style')}</h3>
                        {renderTags(item.style_semantics, editing ? 'style_semantics' : null)}
                    </div>

                    <div>
                        <h3 className="text-sm font-medium text-zinc-500">{t('clothesDetail.season')}</h3>
                        {renderTags(item.season_semantics, editing ? 'season_semantics' : null)}
                    </div>

                    <div>
                        <h3 className="text-sm font-medium text-zinc-500">{t('clothesDetail.usage')}</h3>
                        {renderTags(item.usage_semantics, editing ? 'usage_semantics' : null)}
                    </div>

                    {editing && (
                        <div className="flex gap-2 pt-2 border-t border-zinc-100 dark:border-zinc-800">
                            <button
                                onClick={saveInline}
                                disabled={saving}
                                className="flex-1 py-2 rounded-lg bg-accent text-white text-sm font-medium hover:opacity-90 disabled:opacity-50 transition-opacity cursor-pointer flex items-center justify-center gap-2"
                            >
                                {saving ? (
                                    <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                ) : (
                                    <><Check size={15} /> {t('clothesDetail.saveInline')}</>
                                )}
                            </button>
                            <button
                                onClick={cancelEdit}
                                className="px-4 py-2 rounded-lg border border-zinc-200 dark:border-zinc-700 text-sm font-medium text-zinc-600 dark:text-zinc-400 hover:bg-zinc-50 dark:hover:bg-zinc-800 transition-colors cursor-pointer flex items-center gap-2"
                            >
                                <X size={15} /> Cancelar
                            </button>
                        </div>
                    )}
                </section>
            </div>
        </div>
    )
}
