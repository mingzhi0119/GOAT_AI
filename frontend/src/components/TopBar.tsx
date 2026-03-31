import { useEffect, useRef, useState, type FC } from 'react'

interface Props {
  /** Current conversation title from server (or derived); null shows placeholder. */
  sessionTitle: string | null
  theme: 'light' | 'dark'
  onToggleTheme: () => void
}

/** Full-width shell header: empty left, centered session title, settings (theme) on the right. */
const TopBar: FC<Props> = ({ sessionTitle, theme, onToggleTheme }) => {
  const [menuOpen, setMenuOpen] = useState(false)
  const wrapRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const close = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setMenuOpen(false)
    }
    document.addEventListener('click', close)
    return () => document.removeEventListener('click', close)
  }, [])

  return (
    <header
      className="flex-shrink-0 flex items-center h-12 px-3 border-b z-20"
      style={{
        borderColor: 'var(--border-color)',
        background: 'var(--bg-sidebar)',
      }}
    >
      <div className="flex-1 min-w-0" aria-hidden="true" />
      <div className="flex-[2] flex justify-center min-w-0 px-2">
        <h1
          className="text-sm font-medium truncate text-center max-w-full"
          style={{
            color: sessionTitle ? 'var(--text-main)' : 'var(--text-muted)',
          }}
          title={sessionTitle ?? undefined}
        >
          {sessionTitle ?? 'New conversation'}
        </h1>
      </div>
      <div className="flex-1 flex justify-end min-w-0" ref={wrapRef}>
        <div className="relative">
          <button
            type="button"
            className="p-2 rounded-lg transition-colors"
            style={{ color: 'var(--text-sidebar)' }}
            aria-label="Settings"
            aria-expanded={menuOpen}
            aria-haspopup="true"
            onClick={e => {
              e.stopPropagation()
              setMenuOpen(o => !o)
            }}
          >
            <SettingsGearIcon />
          </button>
          {menuOpen && (
            <div
              className="absolute right-0 mt-1 py-1 rounded-lg shadow-lg min-w-[10rem] border text-sm z-50"
              style={{
                background: 'var(--bg-sidebar)',
                borderColor: 'rgba(255,255,255,0.15)',
                color: 'var(--text-sidebar)',
              }}
              role="menu"
            >
              <button
                type="button"
                className="w-full text-left px-3 py-2 hover:opacity-90 flex items-center gap-2"
                style={{ background: 'transparent' }}
                role="menuitem"
                onClick={() => {
                  onToggleTheme()
                  setMenuOpen(false)
                }}
              >
                {theme === 'light' ? <MoonIcon /> : <SunIcon />}
                <span>{theme === 'light' ? 'Dark mode' : 'Light mode'}</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}

const SettingsGearIcon = () => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="20"
    height="20"
    fill="none"
    viewBox="0 0 24 24"
    strokeWidth={1.5}
    stroke="currentColor"
    aria-hidden="true"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.37.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.37-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.217.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z"
    />
    <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
  </svg>
)

const MoonIcon = () => (
  <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
    <path d="M6 .278a.768.768 0 0 1 .08.858 7.208 7.208 0 0 0-.878 3.46c0 4.021 3.278 7.277 7.318 7.277.527 0 1.04-.055 1.533-.16a.787.787 0 0 1 .81.316.733.733 0 0 1-.031.893A8.349 8.349 0 0 1 8.344 16C3.734 16 0 12.286 0 7.71 0 4.266 2.114 1.312 5.124.06A.752.752 0 0 1 6 .278z" />
  </svg>
)

const SunIcon = () => (
  <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
    <path d="M8 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM8 0a.5.5 0 0 1 .5.5v2a.5.5 0 0 1-1 0v-2A.5.5 0 0 1 8 0zm0 13a.5.5 0 0 1 .5.5v2a.5.5 0 0 1-1 0v-2A.5.5 0 0 1 8 13zm8-5a.5.5 0 0 1-.5.5h-2a.5.5 0 0 1 0-1h2a.5.5 0 0 1 .5.5zM3 8a.5.5 0 0 1-.5.5h-2a.5.5 0 0 1 0-1h2A.5.5 0 0 1 3 8zm10.657-5.657a.5.5 0 0 1 0 .707l-1.414 1.415a.5.5 0 1 1-.707-.708l1.414-1.414a.5.5 0 0 1 .707 0zm-9.193 9.193a.5.5 0 0 1 0 .707L3.05 13.657a.5.5 0 0 1-.707-.707l1.414-1.414a.5.5 0 0 1 .707 0zm9.193 2.121a.5.5 0 0 1-.707 0l-1.414-1.414a.5.5 0 0 1 .707-.707l1.414 1.414a.5.5 0 0 1 0 .707zM4.464 4.465a.5.5 0 0 1-.707 0L2.343 3.05a.5.5 0 1 1 .707-.707l1.414 1.414a.5.5 0 0 1 0 .707z" />
  </svg>
)

export default TopBar
