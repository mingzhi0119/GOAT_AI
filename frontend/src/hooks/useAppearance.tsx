import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type PropsWithChildren,
} from 'react'
import {
  APPEARANCE_STORAGE_KEY,
  DEFAULT_APPEARANCE_CONFIG,
  applyAppearanceToRoot,
  getAppearanceSummary,
  getSystemPrefersDark,
  loadStoredAppearance,
  persistAppearanceConfig,
  resolveThemeMode,
  sanitizeAppearanceConfig,
  type AppearanceConfig,
  type ResolvedThemeMode,
} from '../utils/appearance'

interface AppearanceContextValue {
  appearance: AppearanceConfig
  effectiveMode: ResolvedThemeMode
  appearanceSummary: string
  setAppearance: (next: AppearanceConfig) => void
  updateAppearance: (patch: Partial<AppearanceConfig>) => void
  resetAppearance: () => void
}

const AppearanceContext = createContext<AppearanceContextValue | null>(null)

function getInitialAppearance(): AppearanceConfig {
  if (typeof window === 'undefined') {
    return DEFAULT_APPEARANCE_CONFIG
  }
  return loadStoredAppearance(window.localStorage)
}

export function AppearanceProvider({ children }: PropsWithChildren) {
  const [appearance, setAppearanceState] = useState<AppearanceConfig>(getInitialAppearance)
  const [prefersDark, setPrefersDark] = useState<boolean>(getSystemPrefersDark)

  useEffect(() => {
    const media = window.matchMedia('(prefers-color-scheme: dark)')
    const handleChange = (event: MediaQueryListEvent) => {
      setPrefersDark(event.matches)
    }

    setPrefersDark(media.matches)
    media.addEventListener('change', handleChange)
    return () => media.removeEventListener('change', handleChange)
  }, [])

  useEffect(() => {
    applyAppearanceToRoot(document.documentElement, appearance, prefersDark)
    persistAppearanceConfig(window.localStorage, appearance)
  }, [appearance, prefersDark])

  const value = useMemo<AppearanceContextValue>(() => {
    const setAppearance = (next: AppearanceConfig) => {
      setAppearanceState(sanitizeAppearanceConfig(next))
    }

    return {
      appearance,
      effectiveMode: resolveThemeMode(appearance.themeMode, prefersDark),
      appearanceSummary: getAppearanceSummary(appearance),
      setAppearance,
      updateAppearance: patch => {
        setAppearanceState(current => sanitizeAppearanceConfig({ ...current, ...patch }))
      },
      resetAppearance: () => {
        setAppearanceState(DEFAULT_APPEARANCE_CONFIG)
      },
    }
  }, [appearance, prefersDark])

  return <AppearanceContext.Provider value={value}>{children}</AppearanceContext.Provider>
}

export function useAppearance(): AppearanceContextValue {
  const context = useContext(AppearanceContext)
  if (!context) {
    throw new Error('useAppearance must be used within an AppearanceProvider')
  }
  return context
}

export { APPEARANCE_STORAGE_KEY }
