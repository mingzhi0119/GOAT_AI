import { invoke } from '@tauri-apps/api/core'

const DESKTOP_PROTOCOLS = new Set(['asset:', 'tauri:'])
const DESKTOP_HOSTNAMES = new Set(['asset.localhost', 'tauri.localhost'])
const DEFAULT_RETRY_DELAYS_MS = [150, 300, 600, 1200]

export type DesktopBootstrapStatus = 'ready' | 'failed'

function currentDesktopCandidateUrl(): URL | null {
  try {
    if (typeof document !== 'undefined' && document.baseURI) {
      return new URL(document.baseURI)
    }
    if (typeof window !== 'undefined' && window.location?.href) {
      return new URL(window.location.href)
    }
  } catch {
    return null
  }
  return null
}

function delay(ms: number): Promise<void> {
  return new Promise(resolve => {
    window.setTimeout(resolve, ms)
  })
}

export function isDesktopRuntime(): boolean {
  const currentUrl = currentDesktopCandidateUrl()
  if (!currentUrl) return false
  return DESKTOP_PROTOCOLS.has(currentUrl.protocol) || DESKTOP_HOSTNAMES.has(currentUrl.hostname)
}

export async function reportDesktopBootstrapStatus(
  status: DesktopBootstrapStatus,
): Promise<void> {
  if (!isDesktopRuntime()) return
  try {
    await invoke('report_frontend_bootstrap_status', { status })
  } catch (error) {
    console.warn('Failed to report desktop bootstrap status', error)
  }
}

export async function retryDesktopBootstrapAction<T>(
  action: () => Promise<T>,
  shouldRetry: (error: unknown) => boolean,
  retryDelaysMs: number[] = DEFAULT_RETRY_DELAYS_MS,
): Promise<T> {
  if (!isDesktopRuntime()) {
    return action()
  }

  let lastError: unknown
  for (let attempt = 0; attempt <= retryDelaysMs.length; attempt += 1) {
    try {
      return await action()
    } catch (error) {
      lastError = error
      if (!shouldRetry(error) || attempt >= retryDelaysMs.length) {
        throw error
      }
      await delay(retryDelaysMs[attempt] ?? 0)
    }
  }

  throw lastError instanceof Error
    ? lastError
    : new Error('Desktop bootstrap retry exhausted without an error payload.')
}
