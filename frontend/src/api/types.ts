/** Frontend API and UI types.
 * Backend-derived contract types are generated under `src/api/generated/openapi.ts`.
 * Keep this file for UI-only unions and frontend-facing adapters where the OpenAPI
 * contract needs narrower or more ergonomic typing.
 */

export type ReasoningLevel = 'low' | 'medium' | 'high'
export type ThemeStyle = 'classic' | 'urochester' | 'thu'

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  /** When true, this user turn is upload-derived tabular file context (preferred over content sniffing). */
  file_context?: boolean
  /** Optional image attachment ids associated with this turn. */
  image_attachment_ids?: string[]
}

export interface HistorySessionMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  image_attachment_ids?: string[]
  artifacts?: ChatArtifact[]
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
  /** Planner-style prompt layer that asks the model to plan before answering. */
  plan_mode?: boolean
  /** Current UI theme style; used by the backend to choose the default assistant persona. */
  theme_style?: ThemeStyle
  /** Ollama sampling options (optional; sent when set from Advanced settings). */
  temperature?: number
  max_tokens?: number
  top_p?: number
  /** Quick = false; Thinking may also use low/medium/high effort levels. */
  think?: boolean | ReasoningLevel
}

export interface HistorySessionItem {
  id: string
  title: string
  model: string
  schema_version: number
  created_at: string
  updated_at: string
  owner_id: string
}

export interface HistorySessionFileContext {
  prompt: string
}

export interface HistorySessionKnowledgeDocument {
  document_id: string
  filename: string
  mime_type: string
}

export type HistoryChartDataSource = 'uploaded' | 'demo' | 'none'

export interface HistorySessionDetail extends HistorySessionItem {
  messages: HistorySessionMessage[]
  chart_spec: ChartSpec | null
  file_context: HistorySessionFileContext | null
  knowledge_documents: HistorySessionKnowledgeDocument[]
  workspace_outputs: WorkbenchWorkspaceOutput[]
  chart_data_source: HistoryChartDataSource | null
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
  supports_thinking: boolean
  /** Ollama-reported context window (tokens), when present in /api/show. */
  context_length: number | null
}

export interface GPUStatus {
  available: boolean
  active: boolean
  message: string
  name: string
  uuid: string
  utilization_gpu: number | null
  memory_used_mb: number | null
  memory_total_mb: number | null
  temperature_c: number | null
  power_draw_w: number | null
}

export interface InferenceLatency {
  chat_avg_ms: number
  chat_sample_count: number
  chat_p50_ms: number
  chat_p95_ms: number
  first_token_avg_ms: number
  first_token_sample_count: number
  first_token_p50_ms: number
  first_token_p95_ms: number
  model_buckets: Record<
    string,
    {
      chat_avg_ms: number
      chat_p50_ms: number
      chat_p95_ms: number
      chat_sample_count: number
      first_token_avg_ms: number
      first_token_p50_ms: number
      first_token_p95_ms: number
      first_token_sample_count: number
    }
  >
}

export interface CodeSandboxFeature {
  policy_allowed: boolean
  allowed_by_config: boolean
  available_on_host: boolean
  effective_enabled: boolean
  provider_name: string
  isolation_level: 'container' | 'host'
  network_policy_enforced: boolean
  deny_reason: string | null
}

export interface RuntimeFeature {
  allowed_by_config: boolean
  available_on_host: boolean
  effective_enabled: boolean
  deny_reason: string | null
}

export interface WorkbenchFeatures {
  agent_tasks: RuntimeFeature
  plan_mode: RuntimeFeature
  browse: RuntimeFeature
  deep_research: RuntimeFeature
  artifact_workspace: RuntimeFeature
  project_memory: RuntimeFeature
  connectors: RuntimeFeature
}

export type WorkbenchWorkspaceOutputKind = 'canvas_document'
export type WorkbenchWorkspaceOutputFormat = 'markdown'

export interface WorkbenchWorkspaceOutput {
  output_id: string
  output_kind: WorkbenchWorkspaceOutputKind
  title: string
  content_format: WorkbenchWorkspaceOutputFormat
  content: string
  created_at: string
  updated_at: string
  metadata: Record<string, unknown>
  artifacts: ChatArtifact[]
}

export interface WorkbenchWorkspaceOutputsResponse {
  outputs: WorkbenchWorkspaceOutput[]
}

export type WorkbenchWorkspaceExportFormat = 'markdown' | 'text' | 'csv' | 'xlsx' | 'docx'

export interface WorkbenchWorkspaceExportRequest {
  format: WorkbenchWorkspaceExportFormat
  filename?: string
}

export interface SystemFeatures {
  code_sandbox: CodeSandboxFeature
  workbench: WorkbenchFeatures
}

export interface DesktopDiagnostics {
  desktop_mode: boolean
  backend_base_url: string | null
  readiness_ok: boolean | null
  failing_checks: string[]
  skipped_checks: string[]
  code_sandbox_effective_enabled: boolean | null
  workbench_effective_enabled: boolean | null
  app_data_dir: string | null
  runtime_root: string | null
  data_dir: string | null
  log_dir: string | null
  log_db_path: string | null
  packaged_shell_log_path: string | null
}

export type CodeSandboxRuntimePreset = 'shell'
export type CodeSandboxExecutionStatus =
  | 'queued'
  | 'running'
  | 'completed'
  | 'failed'
  | 'denied'
  | 'cancelled'
export type CodeSandboxExecutionMode = 'sync' | 'async'
export type CodeSandboxNetworkPolicy = 'disabled' | 'allowlist' | 'enabled'

export interface CodeSandboxInlineFile {
  filename: string
  content: string
}

export interface CodeSandboxOutputFile {
  path: string
  byte_size: number
}

export interface CodeSandboxExecRequest {
  execution_mode?: CodeSandboxExecutionMode
  runtime_preset?: CodeSandboxRuntimePreset
  code?: string
  command?: string
  stdin?: string
  timeout_sec?: number
  network_policy?: CodeSandboxNetworkPolicy
  files?: CodeSandboxInlineFile[]
}

export interface CodeSandboxExecutionResponse {
  execution_id: string
  status: CodeSandboxExecutionStatus
  execution_mode: CodeSandboxExecutionMode
  runtime_preset: CodeSandboxRuntimePreset
  network_policy: CodeSandboxNetworkPolicy
  created_at: string
  updated_at: string
  started_at: string | null
  finished_at: string | null
  provider_name: string
  isolation_level: 'container' | 'host'
  network_policy_enforced: boolean
  exit_code: number | null
  stdout: string
  stderr: string
  timed_out: boolean
  error_detail: string | null
  output_files: CodeSandboxOutputFile[]
}

export interface CodeSandboxExecutionEvent {
  sequence: number
  event_type: string
  created_at: string
  status: CodeSandboxExecutionStatus | null
  message: string | null
  metadata: Record<string, unknown>
}

export interface CodeSandboxExecutionEventsResponse {
  execution_id: string
  events: CodeSandboxExecutionEvent[]
}

export interface CodeSandboxLogStreamEvent {
  type: 'stdout' | 'stderr' | 'status' | 'done'
  execution_id?: string
  sequence?: number
  created_at?: string
  chunk?: string
  status?: CodeSandboxExecutionStatus
  provider_name?: string
  updated_at?: string
  timed_out?: boolean
}

/** Ollama sampling options (Advanced settings); maps to backend ChatRequest fields. */
export interface OllamaOptionsPayload {
  temperature: number
  max_tokens: number
  top_p: number
  think?: boolean | ReasoningLevel
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

/** Model reasoning trace (Ollama thinking); shown collapsed in the UI. */
export interface ChatThinkingStreamEvent {
  type: 'thinking'
  token: string
}

export interface ChatChartStreamEvent {
  type: 'chart_spec'
  chart: ChartSpec
}

export interface ChatArtifact {
  artifact_id: string
  filename: string
  mime_type: string
  byte_size: number
  download_url: string
  label?: string
  source_message_id?: string
}

export interface ChatArtifactStreamEvent extends ChatArtifact {
  type: 'artifact'
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
  | ChatThinkingStreamEvent
  | ChatChartStreamEvent
  | ChatArtifactStreamEvent
  | ChatDoneStreamEvent
  | ChatErrorStreamEvent

/** UI-only message shape: extends ChatMessage with a stable DOM key. */
export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  /** UI-only timestamp used for message chrome like copy controls. */
  createdAt?: string
  /** Accumulated model thinking / reasoning trace (not shown inline). */
  thinkingContent?: string
  /** Whether the UI should render the Thinking disclosure for this message. */
  showThinking?: boolean
  artifacts?: ChatArtifact[]
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
