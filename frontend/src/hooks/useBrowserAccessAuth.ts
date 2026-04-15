import { useCallback, useEffect, useState } from 'react'
import { clearStoredProtectedAccess } from '../api/auth'
import {
  BrowserAuthApiError,
  completeGoogleBrowserAuth,
  fetchBrowserAuthSession,
  fetchGoogleOAuthUrl,
  loginAccountBrowserAuth,
  loginSharedBrowserAuth,
  logoutBrowserAuth,
} from '../api/browserAuth'
import { API_AUTH_REQUIRED_EVENT } from '../api/http'
import type { BrowserAuthSession } from '../api/types'
import { navigateToExternalUrl } from '../utils/browserNavigation'
import { retryDesktopBootstrapAction } from '../utils/desktopBootstrap'
import { clearBrowserPrivateState } from './browserPrivateState'

const GOOGLE_CALLBACK_QUERY_KEYS = [
  'code',
  'state',
  'scope',
  'authuser',
  'prompt',
  'error',
  'error_description',
] as const

const DEFAULT_UNAUTHENTICATED_SESSION: BrowserAuthSession = {
  auth_required: true,
  authenticated: false,
  expires_at: null,
  available_login_methods: [],
  active_login_method: null,
  user: null,
}

interface GoogleCallbackParams {
  code: string | null
  state: string | null
  error: string | null
  errorDescription: string | null
}

function toUnauthenticatedSession(
  session: BrowserAuthSession | null | undefined,
): BrowserAuthSession {
  if (!session) return DEFAULT_UNAUTHENTICATED_SESSION
  return {
    ...session,
    authenticated: false,
    expires_at: null,
    active_login_method: null,
    user: null,
  }
}

function getGoogleCallbackParams(): GoogleCallbackParams {
  if (typeof window === 'undefined') {
    return {
      code: null,
      state: null,
      error: null,
      errorDescription: null,
    }
  }
  const url = new URL(window.location.href)
  return {
    code: url.searchParams.get('code'),
    state: url.searchParams.get('state'),
    error: url.searchParams.get('error'),
    errorDescription: url.searchParams.get('error_description'),
  }
}

function clearGoogleCallbackParams(): void {
  if (typeof window === 'undefined') return
  const url = new URL(window.location.href)
  let changed = false
  for (const key of GOOGLE_CALLBACK_QUERY_KEYS) {
    if (!url.searchParams.has(key)) continue
    url.searchParams.delete(key)
    changed = true
  }
  if (!changed) return
  const nextSearch = url.searchParams.toString()
  const nextUrl = `${url.pathname}${nextSearch ? `?${nextSearch}` : ''}${url.hash}`
  window.history.replaceState(window.history.state, document.title, nextUrl)
}

function mapGoogleRedirectError(error: string | null, errorDescription: string | null): string {
  if (!error) return 'Google login failed.'
  if (error === 'access_denied') return 'Google login was canceled.'
  if (errorDescription && errorDescription.trim()) return errorDescription.trim()
  return 'Google login failed.'
}

function mapBrowserAuthError(error: unknown, fallback: string): string {
  if (error instanceof BrowserAuthApiError) {
    switch (error.code) {
      case 'AUTH_INVALID_ACCESS_PASSWORD':
        return 'Shared password is incorrect.'
      case 'AUTH_INVALID_ACCOUNT_CREDENTIALS':
        return 'Email or password is incorrect.'
      case 'AUTH_INVALID_GOOGLE_STATE':
        return 'Google login session expired. Please try again.'
      case 'AUTH_INVALID_GOOGLE_TOKEN':
        return 'Google login could not be verified. Please try again.'
      case 'RATE_LIMITED':
        return 'Too many login attempts. Please wait a moment and try again.'
      default:
        return error.message || fallback
    }
  }
  if (error instanceof Error) return error.message || fallback
  return fallback
}

export interface UseBrowserAccessAuthReturn {
  session: BrowserAuthSession | null
  isLoading: boolean
  isSubmitting: boolean
  error: string | null
  shellKey: number
  refresh: () => Promise<void>
  loginShared: (password: string) => Promise<void>
  loginAccount: (email: string, password: string) => Promise<void>
  startGoogleLogin: () => Promise<void>
  logout: () => Promise<void>
}

export function useBrowserAccessAuth(): UseBrowserAccessAuthReturn {
  const [session, setSession] = useState<BrowserAuthSession | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [shellKey, setShellKey] = useState(0)

  const applySession = useCallback((next: BrowserAuthSession) => {
    if (next.auth_required) {
      clearStoredProtectedAccess()
    }
    if (next.auth_required && !next.authenticated) {
      clearBrowserPrivateState()
    }
    setSession(next)
  }, [])

  const expireBrowserSession = useCallback(() => {
    clearBrowserPrivateState()
    setSession(previous => toUnauthenticatedSession(previous))
    setShellKey(previous => previous + 1)
  }, [])

  const loadCurrentSession = useCallback(
    () =>
      retryDesktopBootstrapAction(
        () => fetchBrowserAuthSession(),
        error => !(error instanceof BrowserAuthApiError),
      ),
    [],
  )

  const refresh = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      applySession(await loadCurrentSession())
    } catch (nextError) {
      setError(mapBrowserAuthError(nextError, 'Failed to load browser session.'))
      setSession(null)
    } finally {
      setIsLoading(false)
    }
  }, [applySession, loadCurrentSession])

  const finishLogin = useCallback((next: BrowserAuthSession) => {
    clearBrowserPrivateState()
    applySession(next)
    setShellKey(previous => previous + 1)
  }, [applySession])

  const loginShared = useCallback(
    async (password: string) => {
      setIsSubmitting(true)
      setError(null)
      try {
        finishLogin(await loginSharedBrowserAuth(password.trim()))
      } catch (nextError) {
        const message = mapBrowserAuthError(nextError, 'Shared password login failed.')
        setError(message)
        throw nextError instanceof Error ? nextError : new Error(message)
      } finally {
        setIsSubmitting(false)
      }
    },
    [finishLogin],
  )

  const loginAccount = useCallback(
    async (email: string, password: string) => {
      setIsSubmitting(true)
      setError(null)
      try {
        finishLogin(await loginAccountBrowserAuth(email.trim(), password))
      } catch (nextError) {
        const message = mapBrowserAuthError(nextError, 'Account login failed.')
        setError(message)
        throw nextError instanceof Error ? nextError : new Error(message)
      } finally {
        setIsSubmitting(false)
      }
    },
    [finishLogin],
  )

  const startGoogleLogin = useCallback(async () => {
    setIsSubmitting(true)
    setError(null)
    try {
      const next = await fetchGoogleOAuthUrl()
      navigateToExternalUrl(next.authorization_url)
    } catch (nextError) {
      const message = mapBrowserAuthError(nextError, 'Failed to start Google login.')
      setError(message)
      throw nextError instanceof Error ? nextError : new Error(message)
    } finally {
      setIsSubmitting(false)
    }
  }, [])

  const logout = useCallback(async () => {
    setIsSubmitting(true)
    setError(null)
    try {
      await logoutBrowserAuth()
    } finally {
      expireBrowserSession()
      setIsSubmitting(false)
    }
  }, [expireBrowserSession])

  useEffect(() => {
    let cancelled = false

    const bootstrap = async () => {
      const callback = getGoogleCallbackParams()
      if (callback.error) {
        clearGoogleCallbackParams()
        const message = mapGoogleRedirectError(callback.error, callback.errorDescription)
        try {
          const next = await loadCurrentSession()
          if (!cancelled) {
            applySession(next)
            setError(message)
          }
        } catch (nextError) {
          if (!cancelled) {
            setError(
              mapBrowserAuthError(
                nextError,
                message || 'Failed to load browser session after Google login.',
              ),
            )
            setSession(null)
          }
        } finally {
          if (!cancelled) {
            setIsLoading(false)
          }
        }
        return
      }

      if (callback.code && callback.state) {
        setError(null)
        try {
          const next = await completeGoogleBrowserAuth(callback.code, callback.state)
          clearGoogleCallbackParams()
          if (!cancelled) {
            finishLogin(next)
          }
        } catch (nextError) {
          clearGoogleCallbackParams()
          const message = mapBrowserAuthError(nextError, 'Google login failed.')
          try {
            const next = await loadCurrentSession()
            if (!cancelled) {
              applySession(next)
              setError(message)
            }
          } catch {
            if (!cancelled) {
              setSession(null)
              setError(message)
            }
          }
        } finally {
          if (!cancelled) {
            setIsLoading(false)
          }
        }
        return
      }

      await refresh()
    }

    void bootstrap()
    return () => {
      cancelled = true
    }
  }, [applySession, finishLogin, loadCurrentSession, refresh])

  useEffect(() => {
    if (!session?.auth_required) return
    const handleAuthRequired = () => {
      expireBrowserSession()
    }
    window.addEventListener(API_AUTH_REQUIRED_EVENT, handleAuthRequired)
    return () => {
      window.removeEventListener(API_AUTH_REQUIRED_EVENT, handleAuthRequired)
    }
  }, [expireBrowserSession, session?.auth_required])

  return {
    session,
    isLoading,
    isSubmitting,
    error,
    shellKey,
    refresh,
    loginShared,
    loginAccount,
    startGoogleLogin,
    logout,
  }
}
