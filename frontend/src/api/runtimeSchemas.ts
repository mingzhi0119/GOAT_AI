import { z } from 'zod'
import type {
  CodeSandboxExecutionEventsResponse,
  CodeSandboxExecutionResponse,
  CodeSandboxFeature,
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
const codeSandboxNetworkPolicies = ['disabled', 'allowlist', 'enabled'] as const

const normalizedNullableStringSchema = z
  .string()
  .nullable()
  .optional()
  .transform(value => value ?? null)

const runtimeFeatureSchema: z.ZodType<RuntimeFeature> = z.object({
  allowed_by_config: z.boolean(),
  available_on_host: z.boolean(),
  effective_enabled: z.boolean(),
  deny_reason: normalizedNullableStringSchema,
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
  deny_reason: normalizedNullableStringSchema,
})

const systemFeaturesSchema: z.ZodType<SystemFeatures> = z.object({
  code_sandbox: codeSandboxFeatureSchema,
  workbench: workbenchFeaturesSchema,
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
  error_detail: normalizedNullableStringSchema,
  output_files: z.array(codeSandboxOutputFileSchema).optional().transform(value => value ?? []),
})

const codeSandboxExecutionEventSchema = z.object({
  sequence: z.number().int(),
  event_type: z.string(),
  created_at: z.string(),
  status: z.enum(codeSandboxExecutionStatuses).nullable().optional().transform(value => value ?? null),
  message: normalizedNullableStringSchema,
  metadata: z.record(z.string(), z.unknown()).optional().transform(value => value ?? {}),
})

const codeSandboxExecutionEventsResponseSchema: z.ZodType<CodeSandboxExecutionEventsResponse> =
  z.object({
    execution_id: z.string(),
    events: z.array(codeSandboxExecutionEventSchema),
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
