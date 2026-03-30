/** API types — mirror the backend Pydantic models exactly. */

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
}

export interface ChatRequest {
  model: string
  messages: ChatMessage[]
}

export interface ModelsResponse {
  models: string[]
}

/** UI-only message shape: extends ChatMessage with a stable DOM key. */
export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  isStreaming?: boolean
}
