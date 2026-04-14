import { useEffect, useMemo, useState, type FormEvent } from 'react'
import type { BrowserAuthSession } from '../api/types'

type LoginPanel = 'shared_password' | 'account'

interface BrowserLoginGateProps {
  appTitle: string
  session: BrowserAuthSession
  isLoading: boolean
  isSubmitting: boolean
  error: string | null
  onLoginShared: (password: string) => Promise<void>
  onLoginAccount: (email: string, password: string) => Promise<void>
  onStartGoogleLogin: () => Promise<void>
  onRetry: () => Promise<void>
}

function getDefaultPanel(session: BrowserAuthSession): LoginPanel {
  if (session.available_login_methods.includes('shared_password')) {
    return 'shared_password'
  }
  return 'account'
}

export default function BrowserLoginGate({
  appTitle,
  session,
  isLoading,
  isSubmitting,
  error,
  onLoginShared,
  onLoginAccount,
  onStartGoogleLogin,
  onRetry,
}: BrowserLoginGateProps) {
  const [activePanel, setActivePanel] = useState<LoginPanel>(getDefaultPanel(session))
  const [sharedPassword, setSharedPassword] = useState('')
  const [email, setEmail] = useState('')
  const [accountPassword, setAccountPassword] = useState('')
  const [localError, setLocalError] = useState<string | null>(null)
  const hasShared = session.available_login_methods.includes('shared_password')
  const hasAccountPassword = session.available_login_methods.includes('account_password')
  const hasGoogle = session.available_login_methods.includes('google')
  const showAccountPanel = hasAccountPassword || hasGoogle
  const showPanelSwitcher = hasShared && showAccountPanel
  const effectivePanel = showPanelSwitcher ? activePanel : getDefaultPanel(session)

  useEffect(() => {
    setActivePanel(getDefaultPanel(session))
  }, [session])

  const helperText = useMemo(() => {
    if (effectivePanel === 'shared_password') {
      return 'Use the shared site password to open a browser-scoped workspace. History stays isolated to this browser session.'
    }
    return 'Sign in with an account for a stable user workspace that carries across browsers and devices.'
  }, [effectivePanel])

  const handleSharedSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const trimmed = sharedPassword.trim()
    if (!trimmed) {
      setLocalError('Enter the shared password.')
      return
    }
    setLocalError(null)
    try {
      await onLoginShared(trimmed)
      setSharedPassword('')
    } catch {
      // API error is surfaced by props.
    }
  }

  const handleAccountSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const trimmedEmail = email.trim()
    if (!trimmedEmail) {
      setLocalError('Enter your email address.')
      return
    }
    if (!accountPassword.trim()) {
      setLocalError('Enter your password.')
      return
    }
    setLocalError(null)
    try {
      await onLoginAccount(trimmedEmail, accountPassword)
      setAccountPassword('')
    } catch {
      // API error is surfaced by props.
    }
  }

  return (
    <div
      className="flex min-h-screen items-center justify-center px-4"
      style={{ background: 'var(--bg-main)' }}
    >
      <div
        className="w-full max-w-lg rounded-[28px] border px-6 py-7 shadow-[0_18px_48px_var(--panel-shadow-color)]"
        style={{
          background: 'var(--composer-menu-bg-strong)',
          borderColor: 'var(--input-border)',
          color: 'var(--text-main)',
          backdropFilter: 'blur(18px)',
        }}
      >
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-[0.1em]" style={{ color: 'var(--text-muted)' }}>
            Browser access
          </p>
          <h1 className="text-2xl font-semibold tracking-[-0.03em]">{appTitle}</h1>
          <p className="text-sm leading-6" style={{ color: 'var(--text-muted)' }}>
            {helperText}
          </p>
        </div>

        {showPanelSwitcher && (
          <div
            className="mt-6 inline-flex rounded-2xl border p-1"
            style={{
              borderColor: 'var(--input-border)',
              background: 'var(--composer-muted-surface)',
            }}
            role="tablist"
            aria-label="Login methods"
          >
            <button
              type="button"
              role="tab"
              aria-selected={effectivePanel === 'shared_password'}
              className="rounded-2xl px-4 py-2 text-sm font-medium"
              style={{
                background:
                  effectivePanel === 'shared_password'
                    ? 'var(--theme-accent)'
                    : 'transparent',
                color:
                  effectivePanel === 'shared_password'
                    ? 'var(--theme-accent-contrast)'
                    : 'var(--text-main)',
              }}
              onClick={() => {
                setLocalError(null)
                setActivePanel('shared_password')
              }}
              disabled={isLoading || isSubmitting}
            >
              Shared Password
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={effectivePanel === 'account'}
              className="rounded-2xl px-4 py-2 text-sm font-medium"
              style={{
                background:
                  effectivePanel === 'account' ? 'var(--theme-accent)' : 'transparent',
                color:
                  effectivePanel === 'account'
                    ? 'var(--theme-accent-contrast)'
                    : 'var(--text-main)',
              }}
              onClick={() => {
                setLocalError(null)
                setActivePanel('account')
              }}
              disabled={isLoading || isSubmitting}
            >
              Account Login
            </button>
          </div>
        )}

        {effectivePanel === 'shared_password' && hasShared ? (
          <form className="mt-6 space-y-4" onSubmit={handleSharedSubmit}>
            <div className="space-y-1.5">
              <label
                htmlFor="shared-access-password"
                className="text-[11px] font-semibold uppercase tracking-[0.08em]"
                style={{ color: 'var(--text-muted)' }}
              >
                Shared password
              </label>
              <input
                id="shared-access-password"
                type="password"
                autoComplete="current-password"
                value={sharedPassword}
                onChange={event => setSharedPassword(event.target.value)}
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
        ) : (
          <div className="mt-6 space-y-4">
            {hasAccountPassword && (
              <form className="space-y-4" onSubmit={handleAccountSubmit}>
                <div className="space-y-1.5">
                  <label
                    htmlFor="account-email"
                    className="text-[11px] font-semibold uppercase tracking-[0.08em]"
                    style={{ color: 'var(--text-muted)' }}
                  >
                    Email
                  </label>
                  <input
                    id="account-email"
                    type="email"
                    autoComplete="email"
                    value={email}
                    onChange={event => setEmail(event.target.value)}
                    className="w-full rounded-2xl border px-3 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500/35"
                    style={{
                      background: 'var(--input-bg)',
                      borderColor: 'var(--input-border)',
                      color: 'var(--text-main)',
                    }}
                    placeholder="you@example.com"
                    disabled={isLoading || isSubmitting}
                  />
                </div>
                <div className="space-y-1.5">
                  <label
                    htmlFor="account-password"
                    className="text-[11px] font-semibold uppercase tracking-[0.08em]"
                    style={{ color: 'var(--text-muted)' }}
                  >
                    Password
                  </label>
                  <input
                    id="account-password"
                    type="password"
                    autoComplete="current-password"
                    value={accountPassword}
                    onChange={event => setAccountPassword(event.target.value)}
                    className="w-full rounded-2xl border px-3 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500/35"
                    style={{
                      background: 'var(--input-bg)',
                      borderColor: 'var(--input-border)',
                      color: 'var(--text-main)',
                    }}
                    placeholder="Enter account password"
                    disabled={isLoading || isSubmitting}
                  />
                </div>
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
                  {isSubmitting ? 'Signing in...' : 'Sign in'}
                </button>
              </form>
            )}

            {hasGoogle && (
              <div
                className={hasAccountPassword ? 'border-t pt-4' : ''}
                style={hasAccountPassword ? { borderColor: 'var(--input-border)' } : undefined}
              >
                {hasAccountPassword && (
                  <p className="mb-3 text-xs font-semibold uppercase tracking-[0.08em]" style={{ color: 'var(--text-muted)' }}>
                    Or continue with
                  </p>
                )}
                <button
                  type="button"
                  className="inline-flex min-w-[11rem] items-center justify-center rounded-2xl border px-4 py-3 text-sm font-medium"
                  style={{
                    borderColor: 'var(--input-border)',
                    color: 'var(--text-main)',
                    background: 'var(--composer-muted-surface)',
                    opacity: isLoading || isSubmitting ? 0.7 : 1,
                  }}
                  onClick={() => {
                    setLocalError(null)
                    void onStartGoogleLogin()
                  }}
                  disabled={isLoading || isSubmitting}
                >
                  Continue with Google
                </button>
              </div>
            )}

            {(localError || error) && (
              <p className="text-sm" style={{ color: 'var(--sidebar-danger)' }}>
                {localError ?? error}
              </p>
            )}

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
        )}
      </div>
    </div>
  )
}
