import type { Message, PersonaSnapshot, ThemeStyle } from '../api/types'

const MESSAGES_KEY = 'goat-ai-messages'
const SESSION_KEY = 'goat-ai-session-id'
const PERSONA_SNAPSHOT_KEY = 'goat-ai-persona-snapshot'
const MAX_STORED = 100

export interface StoredPersonaSnapshot {
  sessionId: string
  snapshot: PersonaSnapshot
  legacyFallback: boolean
}

function isThemeStyle(value: unknown): value is ThemeStyle {
  return value === 'classic' || value === 'urochester' || value === 'thu'
}

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

export function loadStoredPersonaSnapshot(): StoredPersonaSnapshot | null {
  try {
    const raw = localStorage.getItem(PERSONA_SNAPSHOT_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as unknown
    if (!parsed || typeof parsed !== 'object') return null
    const sessionId = Reflect.get(parsed, 'sessionId')
    const snapshot = Reflect.get(parsed, 'snapshot')
    const legacyFallback = Reflect.get(parsed, 'legacyFallback')
    if (typeof sessionId !== 'string' || !sessionId.trim()) return null
    if (!snapshot || typeof snapshot !== 'object') return null
    const themeStyle = Reflect.get(snapshot, 'theme_style')
    const systemInstruction = Reflect.get(snapshot, 'system_instruction')
    if (!isThemeStyle(themeStyle) || typeof systemInstruction !== 'string') return null
    return {
      sessionId,
      snapshot: {
        theme_style: themeStyle,
        system_instruction: systemInstruction,
      },
      legacyFallback: legacyFallback === true,
    }
  } catch {
    return null
  }
}

export function persistPersonaSnapshot(snapshotState: StoredPersonaSnapshot | null): void {
  if (!snapshotState) {
    localStorage.removeItem(PERSONA_SNAPSHOT_KEY)
    return
  }
  try {
    localStorage.setItem(PERSONA_SNAPSHOT_KEY, JSON.stringify(snapshotState))
  } catch {
    // localStorage might be full or unavailable
  }
}

export function clearStoredChatState(): void {
  localStorage.removeItem(MESSAGES_KEY)
  localStorage.removeItem(SESSION_KEY)
  localStorage.removeItem(PERSONA_SNAPSHOT_KEY)
}
