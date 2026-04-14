import { useState, type FormEvent } from 'react'

interface SharedAccessLoginGateProps {
  appTitle: string
  isLoading: boolean
  isSubmitting: boolean
  error: string | null
  onLogin: (password: string) => Promise<void>
  onRetry: () => Promise<void>
}

export default function SharedAccessLoginGate({
  appTitle,
  isLoading,
  isSubmitting,
  error,
  onLogin,
  onRetry,
}: SharedAccessLoginGateProps) {
  const [password, setPassword] = useState('')
  const [localError, setLocalError] = useState<string | null>(null)

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const trimmed = password.trim()
    if (!trimmed) {
      setLocalError('Enter the shared access password.')
      return
    }
    setLocalError(null)
    try {
      await onLogin(trimmed)
      setPassword('')
    } catch {
      // surface the API error from props
    }
  }

  return (
    <div
      className="flex min-h-screen items-center justify-center px-4"
      style={{ background: 'var(--bg-main)' }}
    >
      <div
        className="w-full max-w-md rounded-[28px] border px-6 py-7 shadow-[0_18px_48px_var(--panel-shadow-color)]"
        style={{
          background: 'var(--composer-menu-bg-strong)',
          borderColor: 'var(--input-border)',
          color: 'var(--text-main)',
          backdropFilter: 'blur(18px)',
        }}
      >
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-[0.1em]" style={{ color: 'var(--text-muted)' }}>
            Shared access
          </p>
          <h1 className="text-2xl font-semibold tracking-[-0.03em]">{appTitle}</h1>
          <p className="text-sm leading-6" style={{ color: 'var(--text-muted)' }}>
            Enter the site password to open a browser-specific chat workspace. Your conversation
            history stays scoped to this browser session.
          </p>
        </div>

        <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
          <div className="space-y-1.5">
            <label
              htmlFor="shared-access-password"
              className="text-[11px] font-semibold uppercase tracking-[0.08em]"
              style={{ color: 'var(--text-muted)' }}
            >
              Password
            </label>
            <input
              id="shared-access-password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={event => setPassword(event.target.value)}
              className="w-full rounded-2xl border px-3 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500/35"
              style={{
                background: 'var(--input-bg)',
                borderColor: 'var(--input-border)',
                color: 'var(--text-main)',
              }}
              placeholder="Enter shared password"
              disabled={isLoading || isSubmitting}
            />
          </div>
          {(localError || error) && (
            <p className="text-sm" style={{ color: 'var(--sidebar-danger)' }}>
              {localError ?? error}
            </p>
          )}
          <div className="flex items-center gap-3">
            <button
              type="submit"
              className="inline-flex min-w-[8rem] items-center justify-center rounded-2xl px-4 py-3 text-sm font-medium"
              style={{
                background: 'var(--theme-accent)',
                color: 'var(--theme-accent-contrast)',
                opacity: isLoading || isSubmitting ? 0.7 : 1,
              }}
              disabled={isLoading || isSubmitting}
            >
              {isSubmitting ? 'Signing in...' : 'Enter GOAT'}
            </button>
            <button
              type="button"
              className="rounded-2xl border px-4 py-3 text-sm"
              style={{
                borderColor: 'var(--input-border)',
                color: 'var(--text-main)',
              }}
              onClick={() => {
                void onRetry()
              }}
              disabled={isLoading || isSubmitting}
            >
              {isLoading ? 'Checking...' : 'Retry'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
