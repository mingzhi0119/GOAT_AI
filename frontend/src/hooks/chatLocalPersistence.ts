import type { Message } from '../api/types'

const MESSAGES_KEY = 'goat-ai-messages'
const SESSION_KEY = 'goat-ai-session-id'
const MAX_STORED = 100

export function loadStoredMessages(): Message[] {
  try {
    const raw = localStorage.getItem(MESSAGES_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as unknown
    if (!Array.isArray(parsed)) return []
    return (parsed as Message[]).filter(message => !message.isStreaming)
  } catch {
    return []
  }
}

export function loadStoredSessionId(): string | null {
  return localStorage.getItem(SESSION_KEY)
}

export function persistMessages(messages: Message[]): void {
  try {
    const toStore = messages.filter(message => !message.isStreaming).slice(-MAX_STORED)
    localStorage.setItem(MESSAGES_KEY, JSON.stringify(toStore))
  } catch {
    // localStorage might be full or unavailable
  }
}

export function persistSessionId(sessionId: string | null): void {
  if (sessionId) {
    localStorage.setItem(SESSION_KEY, sessionId)
    return
  }
  localStorage.removeItem(SESSION_KEY)
}

export function clearStoredChatState(): void {
  localStorage.removeItem(MESSAGES_KEY)
  localStorage.removeItem(SESSION_KEY)
}
