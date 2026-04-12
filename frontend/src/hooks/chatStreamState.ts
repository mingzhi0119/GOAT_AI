import type { ChatMessage, ChatStreamEvent, ChartSpec, Message } from '../api/types'

const DEFAULT_IMAGE_PROMPT = 'What do you see in this image?'

export function buildUserText(content: string, imageAttachmentIds?: string[]): string {
  const trimmed = content.trim()
  if (trimmed) return trimmed
  return imageAttachmentIds && imageAttachmentIds.length > 0 ? DEFAULT_IMAGE_PROMPT : ''
}

export function buildHistoryMessages(messages: Message[]): ChatMessage[] {
  return messages.map(message => ({
    role: message.role,
    content: message.content,
    ...(message.file_context ? { file_context: true as const } : {}),
    ...(message.image_attachment_ids && message.image_attachment_ids.length > 0
      ? { image_attachment_ids: message.image_attachment_ids }
      : {}),
  }))
}

export function buildUserMessage(content: string, imageAttachmentIds?: string[]): Message {
  return {
    id: crypto.randomUUID(),
    role: 'user',
    content,
    createdAt: new Date().toISOString(),
    ...(imageAttachmentIds && imageAttachmentIds.length > 0
      ? { image_attachment_ids: imageAttachmentIds }
      : {}),
  }
}

export function createAssistantStreamingMessage(showThinking?: boolean): Message {
  return {
    id: crypto.randomUUID(),
    role: 'assistant',
    content: '',
    createdAt: new Date().toISOString(),
    isStreaming: true,
    artifacts: [],
    showThinking,
  }
}

export function applyStreamEvent(
  messages: Message[],
  messageId: string,
  event: ChatStreamEvent,
  onChartSpec?: (spec: ChartSpec) => void,
): Message[] {
  switch (event.type) {
    case 'token':
      return messages.map(message =>
        message.id === messageId
          ? { ...message, content: message.content + event.token }
          : message,
      )
    case 'thinking':
      return messages.map(message =>
        message.id === messageId
          ? {
              ...message,
              thinkingContent: (message.thinkingContent ?? '') + event.token,
            }
          : message,
      )
    case 'artifact': {
      const { type: _type, ...artifact } = event
      return messages.map(message =>
        message.id === messageId
          ? { ...message, artifacts: [...(message.artifacts ?? []), artifact] }
          : message,
      )
    }
    case 'chart_spec':
      onChartSpec?.(event.chart)
      return messages
    case 'error':
      return messages.map(message =>
        message.id === messageId
          ? { ...message, content: event.message, isError: true }
          : message,
      )
    default:
      return messages
  }
}

export function markStreamError(messages: Message[], messageId: string, errorMessage: string): Message[] {
  return messages.map(message =>
    message.id === messageId ? { ...message, content: errorMessage, isError: true } : message,
  )
}

export function finalizeStreamingMessage(messages: Message[], messageId: string): Message[] {
  return messages.map(message =>
    message.id === messageId ? { ...message, isStreaming: false } : message,
  )
}
