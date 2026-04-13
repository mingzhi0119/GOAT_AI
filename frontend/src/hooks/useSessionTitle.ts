import { useMemo } from 'react'
import { truncateSessionTitle } from '../utils/sessionTitle'

interface SessionTitleMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  isStreaming?: boolean
  hidden?: boolean
}

interface SessionTitleHistoryItem {
  id: string
  title: string
}

interface UseSessionTitleArgs {
  sessionId: string | null
  messages: SessionTitleMessage[]
  historySessions: SessionTitleHistoryItem[]
}

export function deriveSessionTitle({
  sessionId,
  messages,
  historySessions,
}: UseSessionTitleArgs): string | null {
  if (!sessionId) return null
  const fromHistory = historySessions.find(session => session.id === sessionId)?.title?.trim()
  if (fromHistory) return fromHistory
  const firstUser = messages.find(
    message =>
      message.role === 'user' &&
      !message.isStreaming &&
      !message.hidden &&
      message.content.trim().length > 0,
  )
  if (!firstUser) return null
  return truncateSessionTitle(firstUser.content)
}

export function useSessionTitle(args: UseSessionTitleArgs): string | null {
  const { historySessions, messages, sessionId } = args
  return useMemo(
    () => deriveSessionTitle({ sessionId, messages, historySessions }),
    [historySessions, messages, sessionId],
  )
}
