/** API types — mirror the backend Pydantic models exactly. */

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  /** When true, this user turn is upload-derived tabular file context (preferred over content sniffing). */
  file_context?: boolean
}

export interface HistorySessionMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  image_attachment_ids?: string[]
}

export interface ChatRequest {
  model: string
  messages: ChatMessage[]
  knowledge_document_ids?: string[]
  /** Uploaded vision image attachment ids for the current user turn. */
  image_attachment_ids?: string[]
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

export interface ModelCapabilitiesResponse {
  model: string
  capabilities: string[]
  supports_tool_calling: boolean
  supports_chart_tools: boolean
  supports_vision: boolean
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

export interface LegacyChartSpec {
  type: 'line' | 'bar'
  title: string
  xKey: string
  series: ChartSeries[]
  data: Record<string, string | number>[]
}

export interface ChartMetaV2 {
  row_count: number
  truncated: boolean
  warnings: string[]
  source_columns: string[]
}

export interface ChartSpecV2 {
  version: '2.0'
  engine: 'echarts'
  kind: 'line' | 'bar' | 'stacked_bar' | 'area' | 'scatter' | 'pie'
  title: string
  description: string
  dataset: Record<string, unknown>[]
  option: Record<string, unknown>
  meta: ChartMetaV2
}

export type ChartSpec = LegacyChartSpec | ChartSpecV2

export interface ChatTokenStreamEvent {
  type: 'token'
  token: string
}

export interface ChatChartStreamEvent {
  type: 'chart_spec'
  chart: ChartSpec
}

export interface ChatDoneStreamEvent {
  type: 'done'
}

export interface ChatErrorStreamEvent {
  type: 'error'
  message: string
}

/** Union of events yielded by streamChat. */
export type ChatStreamEvent =
  | ChatTokenStreamEvent
  | ChatChartStreamEvent
  | ChatDoneStreamEvent
  | ChatErrorStreamEvent

/** UI-only message shape: extends ChatMessage with a stable DOM key. */
export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  /** Set when this user turn included vision image attachments (for UI hints). */
  image_attachment_ids?: string[]
  /** Mirrors API `file_context` when sending hidden upload context to the backend. */
  file_context?: boolean
  isStreaming?: boolean
  isError?: boolean
  /**
   * Hidden messages are kept in state so they are sent to the LLM as history
   * (e.g. the injected file-context prompt and its "I have loaded" ack), but
   * are never rendered in the chat window.
   */
  hidden?: boolean
}
