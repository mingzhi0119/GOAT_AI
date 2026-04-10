import type { HistorySessionDetail } from '../api/history'
import type { Message } from '../api/types'
import type { FileContextItem } from '../hooks/useFileContext'

export const FILE_CONTEXT_REPLY = 'I have loaded the file context.'

export function hydrateHistorySession(session: HistorySessionDetail): Message[] {
  const mapped: Message[] = []
  const fallbackCreatedAt = session.updated_at || session.created_at

  const fileContextPrompt = session.file_context?.prompt?.trim()
  if (fileContextPrompt) {
    mapped.push({
      id: crypto.randomUUID(),
      role: 'user',
      content: fileContextPrompt,
      createdAt: session.created_at,
      hidden: true,
      file_context: true,
    })
    mapped.push({
      id: crypto.randomUUID(),
      role: 'assistant',
      content: FILE_CONTEXT_REPLY,
      createdAt: session.created_at,
      hidden: true,
    })
  }

  for (const message of session.messages) {
    if (message.role !== 'user' && message.role !== 'assistant') continue
    const ids = message.image_attachment_ids
    mapped.push({
      id: crypto.randomUUID(),
      role: message.role,
      content: message.content,
      createdAt: fallbackCreatedAt,
      ...(message.artifacts && message.artifacts.length > 0 ? { artifacts: message.artifacts } : {}),
      ...(ids && ids.length > 0 ? { image_attachment_ids: ids } : {}),
    })
  }

  return mapped
}

export function historyKnowledgeAttachments(session: HistorySessionDetail): FileContextItem[] {
  return session.knowledge_documents.map(document => ({
    id: crypto.randomUUID(),
    filename: document.filename,
    documentId: document.document_id,
    retrievalMode: 'knowledge_rag',
    bindingMode: 'idle',
    status: 'ready',
  }))
}
