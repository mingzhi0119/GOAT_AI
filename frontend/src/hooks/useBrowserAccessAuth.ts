import { useCallback, useEffect, useState } from 'react'
import { clearStoredProtectedAccess } from '../api/auth'
import {
  fetchBrowserAuthSession,
  loginBrowserAuth,
  logoutBrowserAuth,
} from '../api/browserAuth'
import { API_AUTH_REQUIRED_EVENT } from '../api/http'
import type { BrowserAuthSession } from '../api/types'
import { clearBrowserPrivateState } from './browserPrivateState'

const UNAUTHENTICATED_SHARED_SESSION: BrowserAuthSession = {
  auth_required: true,
  authenticated: false,
  expires_at: null,
}

export interface UseBrowserAccessAuthReturn {
  session: BrowserAuthSession | null
  isLoading: boolean
  isSubmitting: boolean
  error: string | null
  shellKey: number
  refresh: () => Promise<void>
  login: (password: string) => Promise<void>
  logout: () => Promise<void>
}

export function useBrowserAccessAuth(): UseBrowserAccessAuthReturn {
  const [session, setSession] = useState<BrowserAuthSession | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [shellKey, setShellKey] = useState(0)

  const expireSharedSession = useCallback(() => {
    clearBrowserPrivateState()
    setSession(UNAUTHENTICATED_SHARED_SESSION)
    setShellKey(previous => previous + 1)
  }, [])

  const refresh = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const next = await fetchBrowserAuthSession()
      if (next.auth_required) {
        clearStoredProtectedAccess()
      }
      if (next.auth_required && !next.authenticated) {
        clearBrowserPrivateState()
      }
      setSession(next)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load browser access session')
      setSession(null)
    } finally {
      setIsLoading(false)
    }
  }, [])

  const login = useCallback(async (password: string) => {
    setIsSubmitting(true)
    setError(null)
    try {
      const next = await loginBrowserAuth(password.trim())
      clearBrowserPrivateState()
      setSession(next)
      setShellKey(previous => previous + 1)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to sign in')
      throw err
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
      expireSharedSession()
      setIsSubmitting(false)
    }
  }, [expireSharedSession])

  useEffect(() => {
    void refresh()
  }, [refresh])

  useEffect(() => {
    if (!session?.auth_required) return
    const handleAuthRequired = () => {
      expireSharedSession()
    }
    window.addEventListener(API_AUTH_REQUIRED_EVENT, handleAuthRequired)
    return () => {
      window.removeEventListener(API_AUTH_REQUIRED_EVENT, handleAuthRequired)
    }
  }, [expireSharedSession, session?.auth_required])

  return {
    session,
    isLoading,
    isSubmitting,
    error,
    shellKey,
    refresh,
    login,
    logout,
  }
}
