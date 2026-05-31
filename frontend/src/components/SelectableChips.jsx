import { useTranslation } from 'react-i18next'

const COLOR_MAP = {
  negro: '#1a1a1a', blanco: '#f5f5f5', gris: '#9ca3af',
  rojo: '#ef4444', azul: '#3b82f6', verde: '#22c55e',
  amarillo: '#eab308', rosa: '#ec4899', naranja: '#f97316',
  marrón: '#8b5cf6', morado: '#a855f7', beige: '#f5deb3',
  dorado: '#d4a017', plateado: '#c0c0c0', estampado: '#6366f1',
}

export default function SelectableChips({ options = [], selected = [], onChange, type, colorChips }) {
  const { t } = useTranslation()

  const getLabel = (value) => {
    if (type === 'color') return t(`wardrobeOptions.colors.${value}`, value)
    return t(`filter.${value}`, value)
  }

  const handleToggle = (value) => {
    if (colorChips) {
      onChange(value === selected ? '' : value)
      return
    }
    const next = selected.includes(value)
      ? selected.filter(v => v !== value)
      : [...selected, value]
    onChange(next)
  }

  return (
    <div className="flex flex-wrap gap-2">
      {options.map(value => {
        const isSelected = colorChips ? selected === value : selected.includes(value)
        const color = COLOR_MAP[value]
        return (
          <button
            key={value}
            type="button"
            onClick={() => handleToggle(value)}
            className={`
              px-3 py-1.5 text-xs rounded-lg border transition-all duration-150 cursor-pointer
              ${isSelected
                ? 'bg-accent text-white border-accent shadow-sm'
                : 'bg-zinc-50 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-300 border-zinc-200 dark:border-zinc-700 hover:border-accent/50 hover:text-accent dark:hover:text-accent'
              }
              ${colorChips && color ? 'pl-2' : ''}
            `}
          >
            <span className="flex items-center gap-1.5">
              {colorChips && color && (
                <span
                  className="inline-block w-3.5 h-3.5 rounded-full border border-zinc-300 dark:border-zinc-600 shrink-0"
                  style={{ backgroundColor: color }}
                />
              )}
              {getLabel(value)}
              {colorChips && isSelected && selected === value && (
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              )}
            </span>
          </button>
        )
      })}
    </div>
  )
}