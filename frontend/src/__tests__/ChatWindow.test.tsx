import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import type { ComponentProps } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  executeCodeSandbox,
  fetchCodeSandboxExecution,
  openCodeSandboxLogStream,
} from '../api/codeSandbox'
import ChatWindow from '../components/ChatWindow'
import type { GPUStatus, InferenceLatency } from '../api/system'
import { getChatLayoutDecisions } from '../utils/chatLayout'
import { brandingConfig } from '../config/branding'

const uploadMediaImageMock = vi.fn()
const streamUploadMock = vi.fn()

vi.mock('../api/media', () => ({
  uploadMediaImage: (...args: unknown[]) => uploadMediaImageMock(...args),
}))

vi.mock('../api/upload', () => ({
  streamUpload: (...args: unknown[]) => streamUploadMock(...args),
}))

vi.mock('../api/codeSandbox', () => ({
  executeCodeSandbox: vi.fn(),
  fetchCodeSandboxExecution: vi.fn(),
  openCodeSandboxLogStream: vi.fn(),
}))

const baseGpuStatus: GPUStatus = {
  available: true,
  active: false,
  message: 'idle',
  name: 'GPU',
  uuid: 'gpu-1',
  utilization_gpu: 0,
  memory_used_mb: 0,
  memory_total_mb: 8192,
  temperature_c: 40,
  power_draw_w: 20,
}

const baseLatency: InferenceLatency = {
  chat_avg_ms: 120,
  chat_sample_count: 1,
  chat_p50_ms: 120,
  chat_p95_ms: 120,
  first_token_avg_ms: 80,
  first_token_sample_count: 1,
  first_token_p50_ms: 80,
  first_token_p95_ms: 80,
  model_buckets: {},
}

function renderChatWindow(overrides: Partial<ComponentProps<typeof ChatWindow>> = {}) {
  const onModelChange = vi.fn()
  const onReasoningLevelChange = vi.fn()
  const onPlanModeChange = vi.fn()

  const view = render(
    <ChatWindow
      messages={[]}
      chartSpec={null}
      isStreaming={false}
      layoutDecisions={getChatLayoutDecisions('wide')}
      models={['test-model', 'backup-model']}
      selectedModel="test-model"
      onModelChange={onModelChange}
      supportsVision
      fileContexts={[]}
      activeFileContext={null}
      onUploadEvent={vi.fn()}
      onSendMessage={vi.fn()}
      onSetFileContextMode={vi.fn()}
      onRemoveFileContext={vi.fn()}
      onStop={vi.fn()}
      gpuStatus={baseGpuStatus}
      gpuError={null}
      inferenceLatency={baseLatency}
      codeSandboxFeature={{
        policy_allowed: true,
        allowed_by_config: true,
        available_on_host: true,
        effective_enabled: true,
        provider_name: 'docker',
        isolation_level: 'container',
        network_policy_enforced: true,
        deny_reason: null,
      }}
      planModeEnabled={false}
      onPlanModeChange={onPlanModeChange}
      reasoningLevel="medium"
      onReasoningLevelChange={onReasoningLevelChange}
      supportsThinking
      thinkingEnabled={false}
      onThinkingEnabledChange={vi.fn()}
      {...overrides}
    />,
  )

  return { ...view, onModelChange, onReasoningLevelChange, onPlanModeChange }
}

describe('ChatWindow composer', () => {
  Element.prototype.scrollIntoView = vi.fn()

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('removes permanent helper copy and disables send until content exists', () => {
    renderChatWindow()

    expect(screen.queryByText(/Attach PNG/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/Enter to Send/i)).not.toBeInTheDocument()

    const sendButton = screen.getByRole('button', { name: /send message/i })
    expect(sendButton).toBeDisabled()

    fireEvent.change(screen.getByPlaceholderText(`Message ${brandingConfig.displayName}`), {
      target: { value: 'Hello there' },
    })

    expect(sendButton).toBeEnabled()
  })

  it('renders composer model and reasoning menu triggers', () => {
    renderChatWindow()

    expect(screen.getByRole('button', { name: /open model menu/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /open reasoning menu/i })).toBeInTheDocument()
  })

  it('shows Thinking Mode in the plus menu when the model supports thinking', () => {
    renderChatWindow({ supportsThinking: true })

    fireEvent.click(screen.getByTitle(/open upload and planning actions/i))
    expect(screen.getByText('Thinking Mode')).toBeInTheDocument()
    expect(screen.getByRole('switch', { name: /thinking mode/i })).toBeInTheDocument()
  })

  it('hides Thinking Mode in the plus menu when the model does not support thinking', () => {
    renderChatWindow({ supportsThinking: false })

    fireEvent.click(screen.getByTitle(/open upload and planning actions/i))
    expect(screen.queryByText('Thinking Mode')).not.toBeInTheDocument()
  })

  it('opens model and reasoning menus and applies the selected options', () => {
    const { onModelChange, onReasoningLevelChange } = renderChatWindow()

    fireEvent.click(screen.getByRole('button', { name: /open model menu/i }))
    fireEvent.click(screen.getByRole('menuitemradio', { name: 'backup-model' }))
    expect(onModelChange).toHaveBeenCalledWith('backup-model')

    fireEvent.click(screen.getByRole('button', { name: /open reasoning menu/i }))
    fireEvent.click(screen.getByRole('menuitemradio', { name: 'High' }))
    expect(onReasoningLevelChange).toHaveBeenCalledWith('high')
  })

  it('keeps upload, manage uploads, plan mode, and thinking mode inside the plus popover', () => {
    renderChatWindow()

    fireEvent.click(screen.getByTitle(/open upload and planning actions/i))

    expect(screen.getByText('Upload Files')).toBeInTheDocument()
    expect(screen.getByText('Run Code')).toBeInTheDocument()
    expect(screen.getByText('Manage Uploads')).toBeInTheDocument()
    expect(screen.getByText('Plan Mode')).toBeInTheDocument()
    expect(screen.getByText('Thinking Mode')).toBeInTheDocument()
  })

  it('shows a compact blue plan indicator beside reasoning only when plan mode is enabled', () => {
    renderChatWindow()
    expect(screen.queryByLabelText(/plan enabled/i)).not.toBeInTheDocument()

    renderChatWindow({ planModeEnabled: true })
    expect(screen.getByRole('button', { name: /plan enabled/i })).toBeInTheDocument()
    expect(screen.getByText('Plan')).toBeInTheDocument()
  })

  it('keeps plan mode switch wired while the blue indicator order is stable', () => {
    const { onPlanModeChange } = renderChatWindow({ planModeEnabled: true })

    fireEvent.click(screen.getByTitle(/open upload and planning actions/i))
    fireEvent.click(screen.getByRole('switch', { name: /plan mode/i }))

    expect(onPlanModeChange).toHaveBeenCalledWith(false)

    const indicatorLabels = screen.getAllByText('Plan')
    expect(indicatorLabels[0]).toBeInTheDocument()
  })

  it('keeps composer popovers mutually exclusive', () => {
    renderChatWindow()

    fireEvent.click(screen.getByTitle(/open upload and planning actions/i))
    expect(screen.getByText('Upload Files')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /open model menu/i }))
    expect(screen.queryByText('Upload Files')).not.toBeInTheDocument()
    expect(screen.getByRole('menu', { name: /model menu/i })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /open reasoning menu/i }))
    expect(screen.queryByRole('menu', { name: /model menu/i })).not.toBeInTheDocument()
    expect(screen.getByRole('menu', { name: /reasoning menu/i })).toBeInTheDocument()

    fireEvent.click(screen.getByTitle(/open upload and planning actions/i))
    fireEvent.click(screen.getByText('Manage Uploads'))
    expect(screen.queryByText('Upload Files')).not.toBeInTheDocument()
    expect(screen.getByText('No uploaded files yet.')).toBeInTheDocument()
  })

  it('keeps the narrow composer footer on one row', () => {
    renderChatWindow({ layoutDecisions: getChatLayoutDecisions('narrow') })

    const controlRow = screen.getByTestId('composer-control-row')
    expect(controlRow.className).toContain('flex')
    expect(controlRow.className).not.toContain('flex-col')
    expect(screen.getByTestId('composer-left-controls')).toBeInTheDocument()
    expect(screen.getByTestId('composer-right-controls')).toBeInTheDocument()
  })

  it('closes open narrow popovers when clicking the textarea area', () => {
    renderChatWindow({ layoutDecisions: getChatLayoutDecisions('narrow') })

    fireEvent.click(screen.getByTitle(/open upload and planning actions/i))
    expect(screen.getByText('Upload Files')).toBeInTheDocument()

    fireEvent.mouseDown(screen.getByTestId('composer-text-surface'))
    expect(screen.queryByText('Upload Files')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /open model menu/i }))
    expect(screen.getByRole('menu', { name: /model menu/i })).toBeInTheDocument()

    fireEvent.mouseDown(screen.getByTestId('composer-text-surface'))
    expect(screen.queryByRole('menu', { name: /model menu/i })).not.toBeInTheDocument()
  })

  it('focuses the textarea when clicking the text surface outside the current text node', () => {
    renderChatWindow()

    const textarea = screen.getByPlaceholderText(`Message ${brandingConfig.displayName}`)
    fireEvent.mouseDown(screen.getByTestId('composer-text-surface'))

    expect(document.activeElement).toBe(textarea)
  })

  it('shows a tooltip for the plan indicator and lets it disable plan mode', () => {
    const { onPlanModeChange } = renderChatWindow({ planModeEnabled: true })

    const planButton = screen.getByRole('button', { name: /plan enabled/i })
    fireEvent.mouseEnter(planButton)
    expect(screen.getByRole('tooltip')).toHaveTextContent('Planning mode is enabled.')

    fireEvent.click(planButton)
    expect(onPlanModeChange).toHaveBeenCalledWith(false)
  })

  it('shows a compact blue thinking indicator, uses hover highlight, and lets it disable thinking mode', () => {
    const onThinkingEnabledChange = vi.fn()
    renderChatWindow({ thinkingEnabled: true, onThinkingEnabledChange })

    const thinkingButton = screen.getByRole('button', { name: /thinking mode enabled/i })
    expect(screen.getByText('Thinking')).toBeInTheDocument()

    fireEvent.mouseEnter(thinkingButton)
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument()
    expect(thinkingButton.style.background).not.toBe('transparent')
    expect(thinkingButton.style.boxShadow).not.toBe('none')

    fireEvent.click(thinkingButton)
    expect(onThinkingEnabledChange).toHaveBeenCalledWith(false)
  })

  it('wires the thinking mode switch in the plus menu', () => {
    const onThinkingEnabledChange = vi.fn()
    renderChatWindow({ supportsThinking: true, thinkingEnabled: false, onThinkingEnabledChange })

    fireEvent.click(screen.getByTitle(/open upload and planning actions/i))
    fireEvent.click(screen.getByRole('switch', { name: /thinking mode/i }))
    expect(onThinkingEnabledChange).toHaveBeenCalledWith(true)
  })

  it('shows a product-style validation message only after unsupported upload', async () => {
    renderChatWindow()

    const input = document.querySelector('input[type="file"]') as HTMLInputElement | null
    expect(input).not.toBeNull()

    fireEvent.change(input!, {
      target: {
        files: [new File(['bad'], 'malware.exe', { type: 'application/octet-stream' })],
      },
    })

    await waitFor(() => {
      expect(
        screen.getByText(
          'Unsupported file type. Please upload a PNG, JPG, WEBP, CSV, XLSX, PDF, DOCX, MD, or TXT file.',
        ),
      ).toBeInTheDocument()
    })
  })

  it('opens the code sandbox panel from the plus menu', () => {
    renderChatWindow()

    fireEvent.click(screen.getByTitle(/open upload and planning actions/i))
    fireEvent.click(screen.getByRole('button', { name: /open code sandbox/i }))

    expect(screen.getByRole('dialog', { name: /code sandbox/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Run' })).toBeInTheDocument()
  })

  it('keeps code sandbox inputs usable after opening the panel', () => {
    renderChatWindow()

    fireEvent.click(screen.getByTitle(/open upload and planning actions/i))
    fireEvent.click(screen.getByRole('button', { name: /open code sandbox/i }))

    const commandInput = screen.getByPlaceholderText(/optional: sh/i)
    const codeArea = screen.getByPlaceholderText("echo 'hello from the sandbox'")
    const stdinArea = screen.getByPlaceholderText(/optional stdin content/i)

    fireEvent.change(commandInput, { target: { value: 'python demo.py' } })
    fireEvent.change(codeArea, { target: { value: 'print(42)' } })
    fireEvent.change(stdinArea, { target: { value: 'stdin data' } })

    expect(commandInput).toHaveValue('python demo.py')
    expect(codeArea).toHaveValue('print(42)')
    expect(stdinArea).toHaveValue('stdin data')
  })

  it('disables the code sandbox action when the feature is unavailable', () => {
    renderChatWindow({
      codeSandboxFeature: {
        policy_allowed: false,
        allowed_by_config: true,
        available_on_host: true,
        effective_enabled: false,
        provider_name: 'docker',
        isolation_level: 'container',
        network_policy_enforced: true,
        deny_reason: 'disabled_by_operator',
      },
    })

    fireEvent.click(screen.getByTitle(/open upload and planning actions/i))
    expect(
      screen.getByRole('button', { name: /code sandbox unavailable/i }),
    ).toBeDisabled()
  })

  it('runs a code sandbox request and renders stdout', async () => {
    vi.mocked(executeCodeSandbox).mockResolvedValue({
      execution_id: 'cs-1',
      status: 'completed',
      execution_mode: 'sync',
      runtime_preset: 'shell',
      network_policy: 'disabled',
      created_at: '2026-04-10T00:00:00Z',
      updated_at: '2026-04-10T00:00:01Z',
      started_at: '2026-04-10T00:00:00Z',
      finished_at: '2026-04-10T00:00:01Z',
      provider_name: 'docker',
      isolation_level: 'container',
      network_policy_enforced: true,
      exit_code: 0,
      stdout: 'hello from sandbox',
      stderr: '',
      timed_out: false,
      error_detail: null,
      output_files: [],
    })
    renderChatWindow()

    fireEvent.click(screen.getByTitle(/open upload and planning actions/i))
    fireEvent.click(screen.getByRole('button', { name: /open code sandbox/i }))
    fireEvent.change(screen.getByPlaceholderText("echo 'hello from the sandbox'"), {
      target: { value: "echo 'hello from sandbox'" },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Run' }))

    await waitFor(() => {
      expect(screen.getByText('hello from sandbox')).toBeInTheDocument()
    })
  })

  it('starts async sandbox monitoring and shows live logs', async () => {
    const stop = vi.fn()
    vi.mocked(executeCodeSandbox).mockResolvedValue({
      execution_id: 'cs-async',
      status: 'queued',
      execution_mode: 'async',
      runtime_preset: 'shell',
      network_policy: 'disabled',
      created_at: '2026-04-10T00:00:00Z',
      updated_at: '2026-04-10T00:00:00Z',
      started_at: null,
      finished_at: null,
      provider_name: '',
      isolation_level: 'container',
      network_policy_enforced: true,
      exit_code: null,
      stdout: '',
      stderr: '',
      timed_out: false,
      error_detail: null,
      output_files: [],
    })
    vi.mocked(fetchCodeSandboxExecution).mockResolvedValue({
      execution_id: 'cs-async',
      status: 'completed',
      execution_mode: 'async',
      runtime_preset: 'shell',
      network_policy: 'disabled',
      created_at: '2026-04-10T00:00:00Z',
      updated_at: '2026-04-10T00:00:01Z',
      started_at: '2026-04-10T00:00:00Z',
      finished_at: '2026-04-10T00:00:01Z',
      provider_name: 'docker',
      isolation_level: 'container',
      network_policy_enforced: true,
      exit_code: 0,
      stdout: 'async log line\n',
      stderr: '',
      timed_out: false,
      error_detail: null,
      output_files: [],
    })
    vi.mocked(openCodeSandboxLogStream).mockImplementation((_id, options) => {
      options.onEvent({ type: 'status', status: 'running' })
      options.onEvent({ type: 'stdout', sequence: 1, chunk: 'async log line\n' })
      options.onEvent({ type: 'done' })
      return stop
    })

    renderChatWindow()

    fireEvent.click(screen.getByTitle(/open upload and planning actions/i))
    fireEvent.click(screen.getByRole('button', { name: /open code sandbox/i }))
    fireEvent.change(screen.getByRole('combobox', { name: /execution mode/i }), {
      target: { value: 'async' },
    })
    fireEvent.change(screen.getByPlaceholderText("echo 'hello from the sandbox'"), {
      target: { value: "echo 'hello from sandbox'" },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Run' }))

    await waitFor(() => {
      expect(screen.getAllByText('async log line').length).toBeGreaterThan(0)
    })
    expect(openCodeSandboxLogStream).toHaveBeenCalledWith(
      'cs-async',
      expect.objectContaining({ afterSequence: 0 }),
    )
    expect(fetchCodeSandboxExecution).toHaveBeenCalledWith('cs-async')
  })

  it('falls back to polling only after the async sandbox stream disconnects', async () => {
    const setIntervalSpy = vi.spyOn(window, 'setInterval')
    vi.mocked(executeCodeSandbox).mockResolvedValue({
      execution_id: 'cs-async-fallback',
      status: 'queued',
      execution_mode: 'async',
      runtime_preset: 'shell',
      network_policy: 'disabled',
      created_at: '2026-04-10T00:00:00Z',
      updated_at: '2026-04-10T00:00:00Z',
      started_at: null,
      finished_at: null,
      provider_name: 'docker',
      isolation_level: 'container',
      network_policy_enforced: true,
      exit_code: null,
      stdout: '',
      stderr: '',
      timed_out: false,
      error_detail: null,
      output_files: [],
    })
    vi.mocked(openCodeSandboxLogStream).mockImplementation((_id, options) => {
      options.onEvent({ type: 'status', status: 'running' })
      return () => undefined
    })

    renderChatWindow()

    fireEvent.click(screen.getByTitle(/open upload and planning actions/i))
    fireEvent.click(screen.getByRole('button', { name: /open code sandbox/i }))
    fireEvent.change(screen.getByRole('combobox', { name: /execution mode/i }), {
      target: { value: 'async' },
    })
    fireEvent.change(screen.getByPlaceholderText("echo 'hello from the sandbox'"), {
      target: { value: "echo 'hello from sandbox'" },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Run' }))

    await waitFor(() => {
      expect(openCodeSandboxLogStream).toHaveBeenCalled()
    })
    const intervalCallsBeforeError = setIntervalSpy.mock.calls.length

    const streamOptions = vi.mocked(openCodeSandboxLogStream).mock.calls[0]?.[1]
    expect(streamOptions?.onError).toBeTypeOf('function')
    streamOptions!.onError!()

    expect(setIntervalSpy.mock.calls.length).toBeGreaterThan(intervalCallsBeforeError)
  })

  it('describes localhost execution as a trusted local fallback instead of an isolated sandbox', () => {
    renderChatWindow({
      codeSandboxFeature: {
        policy_allowed: true,
        allowed_by_config: true,
        available_on_host: true,
        effective_enabled: true,
        provider_name: 'localhost',
        isolation_level: 'host',
        network_policy_enforced: false,
        deny_reason: null,
      },
    })

    fireEvent.click(screen.getByTitle(/open upload and planning actions/i))
    expect(screen.getByText(/trusted-dev fallback/i)).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /open code sandbox/i }))
    expect(screen.getByText(/does not provide full sandbox isolation/i)).toBeInTheDocument()
  })

  it('adds modal semantics and Escape close for the code sandbox panel', async () => {
    renderChatWindow()

    fireEvent.click(screen.getByTitle(/open upload and planning actions/i))
    fireEvent.click(screen.getByRole('button', { name: /open code sandbox/i }))

    const dialog = screen.getByRole('dialog', { name: /code sandbox/i })
    expect(dialog).toHaveAttribute('aria-modal', 'true')

    fireEvent.keyDown(dialog, { key: 'Escape' })
    expect(screen.queryByRole('dialog', { name: /code sandbox/i })).not.toBeInTheDocument()
  })
})
