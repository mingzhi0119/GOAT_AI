import { z } from 'zod'
import type {
  BrowserAuthSession,
  BrowserAuthUser,
  ChatStreamEvent,
  CodeSandboxExecutionEventsResponse,
  CodeSandboxExecutionResponse,
  CodeSandboxFeature,
  CodeSandboxLogStreamEvent,
  DesktopDiagnostics,
  GPUStatus,
  GoogleOAuthUrlResponse,
  HistorySessionDetail,
  HistorySessionItem,
  InferenceLatency,
  ModelCapabilitiesResponse,
  ModelsResponse,
  RuntimeFeature,
  SystemFeatures,
  WorkbenchFeatures,
} from './types'

const codeSandboxIsolationLevels = ['container', 'host'] as const
const codeSandboxExecutionStatuses = [
  'queued',
  'running',
  'completed',
  'failed',
  'denied',
  'cancelled',
] as const
const codeSandboxExecutionModes = ['sync', 'async'] as const
const codeSandboxNetworkPolicies = ['disabled'] as const
const chatKinds = ['line', 'bar', 'stacked_bar', 'area', 'scatter', 'pie'] as const
const historyChartDataSources = ['uploaded', 'demo', 'none'] as const
const codeSandboxLogEventTypes = ['stdout', 'stderr', 'status', 'done'] as const
const browserLoginMethods = ['shared_password', 'account_password', 'google'] as const
const browserAuthProviders = ['local', 'google'] as const

const unknownRecordSchema = z.record(z.string(), z.unknown())
const stringOrNumberRecordSchema = z.record(z.string(), z.union([z.string(), z.number()]))
const optionalNullableStringSchema = z
  .string()
  .nullable()
  .optional()
  .transform(value => value ?? null)
const optionalNullableStringToUndefinedSchema = z
  .string()
  .nullish()
  .transform(value => value ?? undefined)
const optionalNullableNumberSchema = z
  .number()
  .nullable()
  .optional()
  .transform(value => value ?? null)
const optionalNullableBooleanSchema = z
  .boolean()
  .nullable()
  .optional()
  .transform(value => value ?? null)

const chatArtifactSchema = z.object({
  artifact_id: z.string(),
  filename: z.string(),
  mime_type: z.string(),
  byte_size: z.number().nonnegative(),
  download_url: z.string(),
  label: optionalNullableStringToUndefinedSchema,
  source_message_id: optionalNullableStringToUndefinedSchema,
})

const chartSeriesSchema = z.object({
  key: z.string(),
  name: z.string(),
})

const legacyChartSpecSchema = z.object({
  type: z.enum(['line', 'bar']),
  title: z.string(),
  xKey: z.string(),
  series: z.array(chartSeriesSchema),
  data: z.array(stringOrNumberRecordSchema),
})

const chartMetaV2Schema = z.object({
  row_count: z.number(),
  truncated: z.boolean(),
  warnings: z.array(z.string()),
  source_columns: z.array(z.string()),
})

const chartSpecV2Schema = z.object({
  version: z.literal('2.0'),
  engine: z.literal('echarts'),
  kind: z.enum(chatKinds),
  title: z.string(),
  description: z.string(),
  dataset: z.array(unknownRecordSchema),
  option: unknownRecordSchema,
  meta: chartMetaV2Schema,
})

const chartSpecSchema = z.union([legacyChartSpecSchema, chartSpecV2Schema])

const runtimeFeatureSchema: z.ZodType<RuntimeFeature> = z.object({
  allowed_by_config: z.boolean(),
  available_on_host: z.boolean(),
  effective_enabled: z.boolean(),
  deny_reason: optionalNullableStringSchema,
})

const workbenchFeaturesSchema: z.ZodType<WorkbenchFeatures> = z.object({
  agent_tasks: runtimeFeatureSchema,
  plan_mode: runtimeFeatureSchema,
  browse: runtimeFeatureSchema,
  deep_research: runtimeFeatureSchema,
  artifact_workspace: runtimeFeatureSchema,
  artifact_exports: runtimeFeatureSchema,
  project_memory: runtimeFeatureSchema,
  connectors: runtimeFeatureSchema,
})

const codeSandboxFeatureSchema: z.ZodType<CodeSandboxFeature> = z.object({
  policy_allowed: z.boolean(),
  allowed_by_config: z.boolean(),
  available_on_host: z.boolean(),
  effective_enabled: z.boolean(),
  provider_name: z.string(),
  isolation_level: z.enum(codeSandboxIsolationLevels),
  network_policy_enforced: z.boolean(),
  deny_reason: optionalNullableStringSchema,
})

const systemFeaturesSchema: z.ZodType<SystemFeatures> = z.object({
  code_sandbox: codeSandboxFeatureSchema,
  workbench: workbenchFeaturesSchema,
})

const gpuStatusSchema = z.object({
  available: z.boolean(),
  active: z.boolean(),
  message: z.string(),
  name: z.string(),
  uuid: z.string(),
  utilization_gpu: optionalNullableNumberSchema,
  memory_used_mb: optionalNullableNumberSchema,
  memory_total_mb: optionalNullableNumberSchema,
  temperature_c: optionalNullableNumberSchema,
  power_draw_w: optionalNullableNumberSchema,
})

const inferenceLatencyBucketSchema = z.object({
  chat_avg_ms: z.number(),
  chat_p50_ms: z.number(),
  chat_p95_ms: z.number(),
  chat_sample_count: z.number(),
  first_token_avg_ms: z.number(),
  first_token_p50_ms: z.number(),
  first_token_p95_ms: z.number(),
  first_token_sample_count: z.number(),
})

const inferenceLatencySchema = z.object({
  chat_avg_ms: z.number(),
  chat_sample_count: z.number(),
  chat_p50_ms: z.number(),
  chat_p95_ms: z.number(),
  first_token_avg_ms: z.number(),
  first_token_sample_count: z.number(),
  first_token_p50_ms: z.number(),
  first_token_p95_ms: z.number(),
  model_buckets: z.record(z.string(), inferenceLatencyBucketSchema),
})

const desktopDiagnosticsSchema = z.object({
  desktop_mode: z.boolean(),
  backend_base_url: optionalNullableStringSchema,
  readiness_ok: optionalNullableBooleanSchema,
  failing_checks: z.array(z.string()).optional().transform(value => value ?? []),
  skipped_checks: z.array(z.string()).optional().transform(value => value ?? []),
  code_sandbox_effective_enabled: optionalNullableBooleanSchema,
  workbench_effective_enabled: optionalNullableBooleanSchema,
  app_data_dir: optionalNullableStringSchema,
  runtime_root: optionalNullableStringSchema,
  data_dir: optionalNullableStringSchema,
  log_dir: optionalNullableStringSchema,
  log_db_path: optionalNullableStringSchema,
  packaged_shell_log_path: optionalNullableStringSchema,
})

const browserAuthUserSchema: z.ZodType<BrowserAuthUser> = z.object({
  id: z.string(),
  email: z.string(),
  display_name: z.string(),
  provider: z.enum(browserAuthProviders),
})

const browserAuthSessionSchema: z.ZodType<BrowserAuthSession> = z.object({
  auth_required: z.boolean(),
  authenticated: z.boolean(),
  expires_at: optionalNullableStringSchema,
  available_login_methods: z
    .array(z.enum(browserLoginMethods))
    .optional()
    .transform(value => value ?? []),
  active_login_method: z
    .enum(browserLoginMethods)
    .nullable()
    .optional()
    .transform(value => value ?? null),
  user: browserAuthUserSchema
    .nullable()
    .optional()
    .transform(value => value ?? null),
})

const googleOAuthUrlResponseSchema: z.ZodType<GoogleOAuthUrlResponse> = z.object({
  authorization_url: z.string(),
  state_expires_at: z.string(),
})

const modelsResponseSchema = z.object({
  models: z.array(z.string()),
})

const modelCapabilitiesResponseSchema = z.object({
  model: z.string(),
  capabilities: z.array(z.string()),
  supports_tool_calling: z.boolean(),
  supports_chart_tools: z.boolean(),
  supports_vision: z.boolean(),
  supports_thinking: z.boolean(),
  context_length: z.number().nullable().optional().transform(value => value ?? null),
})

const mediaUploadResponseSchema = z.object({
  attachment_id: z.string(),
  filename: z.string(),
  mime_type: z.string(),
  byte_size: z.number().nonnegative(),
  width_px: optionalNullableNumberSchema,
  height_px: optionalNullableNumberSchema,
})

const historySessionItemSchema = z.object({
  id: z.string(),
  title: z.string(),
  model: z.string(),
  schema_version: z.number(),
  created_at: z.string(),
  updated_at: z.string(),
  owner_id: z.string(),
})

const historySessionMessageSchema = z.object({
  role: z.enum(['user', 'assistant', 'system']),
  content: z.string(),
  image_attachment_ids: z.array(z.string()).optional(),
  artifacts: z.array(chatArtifactSchema).optional(),
})

const historySessionFileContextSchema = z.object({
  prompt: z.string(),
})

const historySessionKnowledgeDocumentSchema = z.object({
  document_id: z.string(),
  filename: z.string(),
  mime_type: z.string(),
})

const workbenchWorkspaceOutputSchema = z.object({
  output_id: z.string(),
  output_kind: z.literal('canvas_document'),
  title: z.string(),
  content_format: z.literal('markdown'),
  content: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
  metadata: unknownRecordSchema.optional().transform(value => value ?? {}),
  artifacts: z.array(chatArtifactSchema).optional().transform(value => value ?? []),
})

const historySessionListResponseSchema = z.object({
  sessions: z.array(historySessionItemSchema).optional().transform(value => value ?? []),
})

const historySessionDetailSchema = historySessionItemSchema.extend({
  messages: z.array(historySessionMessageSchema),
  chart_spec: chartSpecSchema.nullable().optional().transform(value => value ?? null),
  file_context: historySessionFileContextSchema
    .nullable()
    .optional()
    .transform(value => value ?? null),
  knowledge_documents: z
    .array(historySessionKnowledgeDocumentSchema)
    .optional()
    .transform(value => value ?? []),
  workspace_outputs: z
    .array(workbenchWorkspaceOutputSchema)
    .optional()
    .transform(value => value ?? []),
  chart_data_source: z
    .enum(historyChartDataSources)
    .nullable()
    .optional()
    .transform(value => value ?? null),
})

const codeSandboxOutputFileSchema = z.object({
  path: z.string(),
  byte_size: z.number().int().nonnegative(),
})

const codeSandboxExecutionResponseSchema: z.ZodType<CodeSandboxExecutionResponse> = z.object({
  execution_id: z.string(),
  status: z.enum(codeSandboxExecutionStatuses),
  execution_mode: z.enum(codeSandboxExecutionModes),
  runtime_preset: z.literal('shell'),
  network_policy: z.enum(codeSandboxNetworkPolicies),
  created_at: z.string(),
  updated_at: z.string(),
  started_at: z.string().nullable().optional().transform(value => value ?? null),
  finished_at: z.string().nullable().optional().transform(value => value ?? null),
  provider_name: z.string(),
  isolation_level: z.enum(codeSandboxIsolationLevels),
  network_policy_enforced: z.boolean(),
  exit_code: z.number().int().nullable().optional().transform(value => value ?? null),
  stdout: z.string(),
  stderr: z.string(),
  timed_out: z.boolean(),
  error_detail: optionalNullableStringSchema,
  output_files: z.array(codeSandboxOutputFileSchema).optional().transform(value => value ?? []),
})

const codeSandboxExecutionEventSchema = z.object({
  sequence: z.number().int(),
  event_type: z.string(),
  created_at: z.string(),
  status: z
    .enum(codeSandboxExecutionStatuses)
    .nullable()
    .optional()
    .transform(value => value ?? null),
  message: optionalNullableStringSchema,
  metadata: unknownRecordSchema.optional().transform(value => value ?? {}),
})

const codeSandboxExecutionEventsResponseSchema: z.ZodType<CodeSandboxExecutionEventsResponse> =
  z.object({
    execution_id: z.string(),
    events: z.array(codeSandboxExecutionEventSchema),
  })

const chatStreamEventSchema = z.discriminatedUnion('type', [
  z.object({
    type: z.literal('token'),
    token: z.string(),
  }),
  z.object({
    type: z.literal('thinking'),
    token: z.string(),
  }),
  z.object({
    type: z.literal('chart_spec'),
    chart: chartSpecSchema,
  }),
  chatArtifactSchema.extend({
    type: z.literal('artifact'),
  }),
  z.object({
    type: z.literal('done'),
  }),
  z.object({
    type: z.literal('error'),
    message: z.string(),
  }),
])

const uploadStreamEventSchema = z.discriminatedUnion('type', [
  z.object({
    type: z.literal('file_prompt'),
    filename: z.string(),
    suffix_prompt: z.string(),
  }),
  z.object({
    type: z.literal('knowledge_ready'),
    filename: z.string(),
    suffix_prompt: z.string(),
    document_id: z.string(),
    ingestion_id: z.string(),
    status: z.string(),
    retrieval_mode: z.string(),
    template_prompt: z.string(),
  }),
  z.object({
    type: z.literal('error'),
    message: z.string(),
  }),
  z.object({
    type: z.literal('done'),
  }),
])

const codeSandboxLogStreamEventSchema: z.ZodType<CodeSandboxLogStreamEvent> = z.object({
  type: z.enum(codeSandboxLogEventTypes),
  execution_id: z.string().optional(),
  sequence: z.number().int().optional(),
  created_at: z.string().optional(),
  chunk: z.string().optional(),
  status: z.enum(codeSandboxExecutionStatuses).optional(),
  provider_name: z.string().optional(),
  updated_at: z.string().optional(),
  timed_out: z.boolean().optional(),
})

function formatIssuePath(path: readonly PropertyKey[]): string {
  return path.length === 0 ? 'root' : path.map(segment => String(segment)).join('.')
}

function buildSchemaErrorMessage(boundaryName: string, error: z.ZodError): string {
  const firstIssue = error.issues[0]
  if (!firstIssue) {
    return `${boundaryName} returned an invalid response payload.`
  }
  return `${boundaryName} returned an invalid response payload at ${formatIssuePath(firstIssue.path)}: ${firstIssue.message}`
}

function parseApiPayload<T>(
  schema: z.ZodType<T>,
  payload: unknown,
  boundaryName: string,
): T {
  const parsed = schema.safeParse(payload)
  if (!parsed.success) {
    throw new Error(buildSchemaErrorMessage(boundaryName, parsed.error))
  }
  return parsed.data
}

export function parseSystemFeaturesResponse(payload: unknown): SystemFeatures {
  return parseApiPayload(systemFeaturesSchema, payload, 'System features API')
}

export function parseGpuStatusResponse(payload: unknown): GPUStatus {
  return parseApiPayload(gpuStatusSchema, payload, 'GPU status API')
}

export function parseInferenceLatencyResponse(payload: unknown): InferenceLatency {
  return parseApiPayload(inferenceLatencySchema, payload, 'Inference latency API')
}

export function parseDesktopDiagnosticsResponse(payload: unknown): DesktopDiagnostics {
  return parseApiPayload(desktopDiagnosticsSchema, payload, 'Desktop diagnostics API')
}

export function parseBrowserAuthSessionResponse(payload: unknown): BrowserAuthSession {
  return parseApiPayload(browserAuthSessionSchema, payload, 'Browser auth session API')
}

export function parseGoogleOAuthUrlResponse(payload: unknown): GoogleOAuthUrlResponse {
  return parseApiPayload(googleOAuthUrlResponseSchema, payload, 'Google OAuth URL API')
}

export function parseModelsResponse(payload: unknown): ModelsResponse {
  return parseApiPayload(modelsResponseSchema, payload, 'Models API')
}

export function parseModelCapabilitiesResponse(
  payload: unknown,
): ModelCapabilitiesResponse {
  return parseApiPayload(
    modelCapabilitiesResponseSchema,
    payload,
    'Model capabilities API',
  )
}

export function parseMediaUploadResponse(payload: unknown) {
  return parseApiPayload(mediaUploadResponseSchema, payload, 'Media upload API')
}

export function parseHistorySessionListResponse(
  payload: unknown,
): HistorySessionItem[] {
  return parseApiPayload(historySessionListResponseSchema, payload, 'History API').sessions
}

export function parseHistorySessionDetailResponse(
  payload: unknown,
): HistorySessionDetail {
  return parseApiPayload(
    historySessionDetailSchema,
    payload,
    'History session API',
  )
}

export function parseCodeSandboxExecutionResponse(
  payload: unknown,
): CodeSandboxExecutionResponse {
  return parseApiPayload(codeSandboxExecutionResponseSchema, payload, 'Code sandbox API')
}

export function parseCodeSandboxExecutionEventsResponse(
  payload: unknown,
): CodeSandboxExecutionEventsResponse {
  return parseApiPayload(
    codeSandboxExecutionEventsResponseSchema,
    payload,
    'Code sandbox events API',
  )
}

export function parseChatStreamEvent(payload: unknown): ChatStreamEvent {
  return parseApiPayload(chatStreamEventSchema, payload, 'Chat API stream')
}

export function parseUploadStreamEvent(payload: unknown) {
  return parseApiPayload(uploadStreamEventSchema, payload, 'Upload API stream')
}

export function parseCodeSandboxLogStreamEvent(
  payload: unknown,
): CodeSandboxLogStreamEvent {
  return parseApiPayload(
    codeSandboxLogStreamEventSchema,
    payload,
    'Code sandbox log stream',
  )
}
