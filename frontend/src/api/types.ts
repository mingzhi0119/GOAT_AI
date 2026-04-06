/** API types — mirror the backend Pydantic models exactly. */

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
}

export interface ChatRequest {
  model: string
  messages: ChatMessage[]
  session_id?: string
  /** Optional user-defined instructions merged into the server system prompt. */
  system_instruction?: string
  /** Ollama sampling options (optional; sent when set from Advanced settings). */
  temperature?: number
  max_tokens?: number
  top_p?: number
}

export interface ModelsResponse {
  models: string[]
}

/** Ollama sampling options (Advanced settings); maps to backend ChatRequest fields. */
export interface OllamaOptionsPayload {
  temperature: number
  max_tokens: number
  top_p: number
}

export interface ChartSeries {
  key: string
  name: string
}

export interface ChartSpec {
  type: 'line' | 'bar'
  title: string
  xKey: string
  series: ChartSeries[]
  data: Record<string, string | number>[]
}

/** Union of events yielded by streamChat: plain token strings or a chart spec. */
export type ChatStreamEvent = string | ChartSpec

/** UI-only message shape: extends ChatMessage with a stable DOM key. */
export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  isStreaming?: boolean
  isError?: boolean
}
