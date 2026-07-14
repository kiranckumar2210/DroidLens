import { Monitor, Moon, Sun } from 'lucide-react'
import type { ThemeMode } from '../../hooks/useTheme'

interface Props {
  theme: ThemeMode
  onChange: (theme: ThemeMode) => void
}

const OPTIONS: { id: ThemeMode; icon: typeof Sun; label: string }[] = [
  { id: 'dark', icon: Moon, label: 'Dark' },
  { id: 'light', icon: Sun, label: 'Light' },
  { id: 'system', icon: Monitor, label: 'System' },
]

export default function ThemeSwitcher({ theme, onChange }: Props) {
  return (
    <div className="theme-switcher" role="group" aria-label="Theme">
      {OPTIONS.map(({ id, icon: Icon, label }) => (
        <button
          key={id}
          type="button"
          className={theme === id ? 'active' : ''}
          onClick={() => onChange(id)}
          title={label}
          aria-label={label}
          aria-pressed={theme === id}
        >
          <Icon size={14} />
        </button>
      ))}
    </div>
  )
}
