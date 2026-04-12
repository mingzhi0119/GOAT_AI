import { useCallback } from 'react'
import type { UploadStreamEvent } from '../api/upload'
import type { UseChatSessionReturn } from './useChatSession'

interface UseChatShellActionsReturn {
  handleDeleteAllHistory: () => void
  handleDeleteConversation: () => void
  handleRefreshHistory: () => void
  handleRenameConversation: () => void
  handleUploadEvent: (event: UploadStreamEvent) => void
}

export function useChatShellActions(session: UseChatSessionReturn): UseChatShellActionsReturn {
  const handleDeleteConversation = useCallback(() => {
    if (!session.sessionId) return
    if (!window.confirm('Delete this saved conversation? This cannot be undone.')) {
      return
    }
    void session.deleteHistorySession(session.sessionId).then(() => {
      session.clearChatSession()
    })
  }, [session])

  const handleRefreshHistory = useCallback(() => {
    void session.refreshHistory()
  }, [session])

  const handleDeleteAllHistory = useCallback(() => {
    if (!window.confirm('Delete all saved conversations? This cannot be undone.')) {
      return
    }
    void session.deleteAllHistory().then(() => {
      session.clearChatSession()
    })
  }, [session])

  const handleRenameConversation = useCallback(() => {
    if (!session.sessionId) return
    const currentTitle = session.sessionTitle ?? 'New conversation'
    const nextTitle = window.prompt('Rename this conversation', currentTitle)
    if (nextTitle == null) return
    const normalizedTitle = nextTitle.trim()
    if (!normalizedTitle || normalizedTitle === currentTitle) return
    void session.renameHistorySession(session.sessionId, normalizedTitle)
  }, [session])

  const handleUploadEvent = useCallback(
    (event: UploadStreamEvent) => {
      if (event.type === 'file_prompt') {
        session.upsertFileContext({
          filename: event.filename,
          suffixPrompt: event.suffix_prompt,
          status: 'processing',
        })
        return
      }
      if (event.type === 'knowledge_ready') {
        session.upsertFileContext({
          filename: event.filename,
          documentId: event.document_id,
          ingestionId: event.ingestion_id,
          retrievalMode: event.retrieval_mode,
          suffixPrompt: event.suffix_prompt,
          templatePrompt: event.template_prompt,
          status: 'ready',
        })
      }
    },
    [session],
  )

  return {
    handleDeleteAllHistory,
    handleDeleteConversation,
    handleRefreshHistory,
    handleRenameConversation,
    handleUploadEvent,
  }
}
