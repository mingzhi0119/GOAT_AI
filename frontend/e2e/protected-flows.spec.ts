import { expect, test, type Page, type Route } from '@playwright/test'

type CapturedHeaders = Record<string, Record<string, string>[]>

const API_KEY_STORAGE_KEY = 'goat-ai-api-key'
const OWNER_ID_STORAGE_KEY = 'goat-ai-owner-id'

function jsonResponse(payload: unknown) {
  return {
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(payload),
  }
}

function sseResponse(frames: string[]) {
  return {
    status: 200,
    headers: {
      'cache-control': 'no-cache',
      'content-type': 'text/event-stream',
    },
    body: frames.join(''),
  }
}

function recordHeaders(store: CapturedHeaders, route: Route): string {
  const pathname = new URL(route.request().url()).pathname
  const entries = store[pathname] ?? []
  entries.push(route.request().headers())
  store[pathname] = entries
  return pathname
}

async function installApiMocks(
  page: Page,
  capturedHeaders: CapturedHeaders,
  options?: {
    codeSandboxEnabled?: boolean
  },
) {
  await page.route('**/api/**', async route => {
    const pathname = new URL(route.request().url()).pathname
    if (!pathname.startsWith('/api/')) {
      await route.continue()
      return
    }
    recordHeaders(capturedHeaders, route)
    const method = route.request().method()
    const codeSandboxEnabled = options?.codeSandboxEnabled ?? false

    if (pathname === '/api/models') {
      await route.fulfill(jsonResponse({ models: ['gemma4:26b'] }))
      return
    }

    if (pathname === '/api/models/capabilities') {
      await route.fulfill(
        jsonResponse({
          model: 'gemma4:26b',
          capabilities: ['thinking'],
          supports_tool_calling: false,
          supports_chart_tools: false,
          supports_vision: false,
          supports_thinking: true,
          context_length: 8192,
        }),
      )
      return
    }

    if (pathname === '/api/history') {
      if (method === 'DELETE') {
        await route.fulfill(jsonResponse({}))
        return
      }
      await route.fulfill(jsonResponse({ sessions: [] }))
      return
    }

    if (pathname === '/api/system/features') {
      await route.fulfill(
        jsonResponse({
          code_sandbox: {
            policy_allowed: true,
            allowed_by_config: codeSandboxEnabled,
            available_on_host: codeSandboxEnabled,
            effective_enabled: codeSandboxEnabled,
            provider_name: codeSandboxEnabled ? 'docker' : 'localhost',
            isolation_level: 'container',
            network_policy_enforced: true,
            deny_reason: null,
          },
          workbench: {
            agent_tasks: {
              allowed_by_config: false,
              available_on_host: false,
              effective_enabled: false,
              deny_reason: null,
            },
            plan_mode: {
              allowed_by_config: false,
              available_on_host: false,
              effective_enabled: false,
              deny_reason: null,
            },
            browse: {
              allowed_by_config: false,
              available_on_host: false,
              effective_enabled: false,
              deny_reason: null,
            },
            deep_research: {
              allowed_by_config: false,
              available_on_host: false,
              effective_enabled: false,
              deny_reason: null,
            },
            artifact_workspace: {
              allowed_by_config: false,
              available_on_host: false,
              effective_enabled: false,
              deny_reason: null,
            },
            artifact_exports: {
              allowed_by_config: false,
              available_on_host: false,
              effective_enabled: false,
              deny_reason: null,
            },
            project_memory: {
              allowed_by_config: false,
              available_on_host: false,
              effective_enabled: false,
              deny_reason: null,
            },
            connectors: {
              allowed_by_config: false,
              available_on_host: false,
              effective_enabled: false,
              deny_reason: null,
            },
          },
        }),
      )
      return
    }

    if (pathname === '/api/system/gpu') {
      await route.fulfill(
        jsonResponse({
          available: true,
          active: false,
          message: 'idle',
          name: 'A100',
          uuid: 'GPU-1',
          utilization_gpu: 0,
          memory_used_mb: 0,
          memory_total_mb: 40960,
          temperature_c: 35,
          power_draw_w: 120,
        }),
      )
      return
    }

    if (pathname === '/api/system/inference') {
      await route.fulfill(
        jsonResponse({
          chat_avg_ms: 10,
          chat_sample_count: 1,
          chat_p50_ms: 10,
          chat_p95_ms: 10,
          first_token_avg_ms: 5,
          first_token_sample_count: 1,
          first_token_p50_ms: 5,
          first_token_p95_ms: 5,
          model_buckets: {},
        }),
      )
      return
    }

    if (pathname === '/api/chat') {
      await route.fulfill(
        sseResponse([
          'data: {"type":"token","token":"Hello from browser e2e"}\n\n',
          'data: {"type":"done"}\n\n',
        ]),
      )
      return
    }

    if (pathname === '/api/upload') {
      await route.fulfill(
        sseResponse([
          'data: {"type":"file_prompt","filename":"budget.csv","suffix_prompt":"Summarize the uploaded file."}\n\n',
          'data: {"type":"knowledge_ready","filename":"budget.csv","suffix_prompt":"Summarize the uploaded file.","document_id":"doc-1","ingestion_id":"ing-1","status":"ready","retrieval_mode":"hybrid","template_prompt":"Use the uploaded file."}\n\n',
          'data: {"type":"done"}\n\n',
        ]),
      )
      return
    }

    if (pathname === '/api/code-sandbox/exec') {
      await route.fulfill(
        jsonResponse({
          execution_id: 'exec-1',
          execution_mode: 'async',
          status: 'running',
          provider_name: 'docker',
          exit_code: null,
          stdout: '',
          stderr: '',
          timed_out: false,
          output_files: [],
          created_at: '2026-04-11T00:00:00Z',
          updated_at: '2026-04-11T00:00:01Z',
        }),
      )
      return
    }

    if (pathname === '/api/code-sandbox/executions/exec-1/logs') {
      await route.fulfill(
        sseResponse([
          'data: {"type":"stdout","sequence":1,"chunk":"hello from sandbox\\n"}\n\n',
          'data: {"type":"status","status":"completed","provider_name":"docker","updated_at":"2026-04-11T00:00:02Z","timed_out":false}\n\n',
          'data: {"type":"done"}\n\n',
        ]),
      )
      return
    }

    if (pathname === '/api/code-sandbox/executions/exec-1') {
      await route.fulfill(
        jsonResponse({
          execution_id: 'exec-1',
          execution_mode: 'async',
          status: 'completed',
          provider_name: 'docker',
          exit_code: 0,
          stdout: 'hello from sandbox\n',
          stderr: '',
          timed_out: false,
          output_files: [],
          created_at: '2026-04-11T00:00:00Z',
          updated_at: '2026-04-11T00:00:02Z',
        }),
      )
      return
    }

    await route.abort()
  })
}

function latestHeaders(capturedHeaders: CapturedHeaders, pathname: string): Record<string, string> {
  const entries = capturedHeaders[pathname]
  if (!entries || entries.length === 0) {
    throw new Error(`Expected headers for ${pathname}, but no request was captured.`)
  }
  return entries[entries.length - 1]!
}

test('protected headers persist across reload and are reused for chat startup flows', async ({
  page,
}) => {
  const capturedHeaders: CapturedHeaders = {}
  const startupPaths = [
    '/api/models',
    '/api/history',
    '/api/system/features',
    '/api/system/gpu',
    '/api/system/inference',
  ]
  await installApiMocks(page, capturedHeaders)

  await page.goto('/')
  await page.getByRole('button', { name: 'Settings' }).click()
  await page.getByLabel('API key').fill('secret-browser')
  await page.getByLabel('Owner ID').fill('owner-browser')
  await page.reload()

  await expect
    .poll(() =>
      startupPaths.every(pathname => {
        const headers = capturedHeaders[pathname]?.at(-1)
        return (
          headers?.['x-goat-api-key'] === 'secret-browser' &&
          headers?.['x-goat-owner-id'] === 'owner-browser'
        )
      }),
    )
    .toBe(true)

  for (const pathname of startupPaths) {
    const headers = latestHeaders(capturedHeaders, pathname)
    expect(headers['x-goat-api-key']).toBe('secret-browser')
    expect(headers['x-goat-owner-id']).toBe('owner-browser')
  }

  await page.locator('textarea[placeholder^="Message "]').fill('Hello protected browser')
  await page.getByRole('button', { name: 'Send message' }).click()

  await expect(page.getByText('Hello from browser e2e')).toBeVisible()
  const chatHeaders = latestHeaders(capturedHeaders, '/api/chat')
  expect(chatHeaders['x-goat-api-key']).toBe('secret-browser')
  expect(chatHeaders['x-goat-owner-id']).toBe('owner-browser')
})

test('knowledge upload keeps protected headers in a real browser flow', async ({ page }) => {
  const capturedHeaders: CapturedHeaders = {}
  await page.addInitScript(
    ({
      apiKey,
      apiKeyStorageKey,
      ownerId,
      ownerIdStorageKey,
    }: {
      apiKey: string
      apiKeyStorageKey: string
      ownerId: string
      ownerIdStorageKey: string
    }) => {
      localStorage.setItem(apiKeyStorageKey, apiKey)
      localStorage.setItem(ownerIdStorageKey, ownerId)
    },
    {
      apiKey: 'secret-upload',
      apiKeyStorageKey: API_KEY_STORAGE_KEY,
      ownerId: 'owner-upload',
      ownerIdStorageKey: OWNER_ID_STORAGE_KEY,
    },
  )
  await installApiMocks(page, capturedHeaders)

  await page.goto('/')
  await page.locator('input[type="file"]').setInputFiles({
    name: 'budget.csv',
    mimeType: 'text/csv',
    buffer: Buffer.from('month,revenue\nJan,10\n', 'utf-8'),
  })

  await expect(page.getByText('budget.csv')).toBeVisible()
  const uploadHeaders = latestHeaders(capturedHeaders, '/api/upload')
  expect(uploadHeaders['x-goat-api-key']).toBe('secret-upload')
  expect(uploadHeaders['x-goat-owner-id']).toBe('owner-upload')
})

test('authenticated code-sandbox log streaming works in a browser runner', async ({
  page,
}) => {
  const capturedHeaders: CapturedHeaders = {}
  await page.addInitScript(
    ({
      apiKey,
      apiKeyStorageKey,
      ownerId,
      ownerIdStorageKey,
    }: {
      apiKey: string
      apiKeyStorageKey: string
      ownerId: string
      ownerIdStorageKey: string
    }) => {
      localStorage.setItem(apiKeyStorageKey, apiKey)
      localStorage.setItem(ownerIdStorageKey, ownerId)
    },
    {
      apiKey: 'secret-sandbox',
      apiKeyStorageKey: API_KEY_STORAGE_KEY,
      ownerId: 'owner-sandbox',
      ownerIdStorageKey: OWNER_ID_STORAGE_KEY,
    },
  )
  await installApiMocks(page, capturedHeaders, { codeSandboxEnabled: true })

  await page.goto('/')
  await page.getByRole('button', { name: 'Open upload and planning actions' }).click()
  await page.getByRole('button', { name: 'Open code sandbox' }).click()
  await page.getByLabel('Execution mode').selectOption('async')
  await page.getByRole('textbox', { name: 'Code' }).fill("echo 'hello from sandbox'")
  await page.getByRole('button', { name: 'Run' }).click()

  await expect(page.getByTestId('sandbox-stdout')).toContainText('hello from sandbox')

  const execHeaders = latestHeaders(capturedHeaders, '/api/code-sandbox/exec')
  expect(execHeaders['x-goat-api-key']).toBe('secret-sandbox')
  expect(execHeaders['x-goat-owner-id']).toBe('owner-sandbox')

  await expect
    .poll(
      () =>
        capturedHeaders['/api/code-sandbox/executions/exec-1/logs']?.length ?? 0,
    )
    .toBeGreaterThan(0)
  const logHeaders = latestHeaders(
    capturedHeaders,
    '/api/code-sandbox/executions/exec-1/logs',
  )
  expect(logHeaders['x-goat-api-key']).toBe('secret-sandbox')
  expect(logHeaders['x-goat-owner-id']).toBe('owner-sandbox')
})
