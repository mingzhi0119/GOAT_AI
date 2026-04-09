import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import type { ComponentProps } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import ChatWindow from '../components/ChatWindow'
import type { GPUStatus, InferenceLatency } from '../api/system'

const uploadMediaImageMock = vi.fn()
const streamUploadMock = vi.fn()

vi.mock('../api/media', () => ({
  uploadMediaImage: (...args: unknown[]) => uploadMediaImageMock(...args),
}))

vi.mock('../api/upload', () => ({
  streamUpload: (...args: unknown[]) => streamUploadMock(...args),
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
      planModeEnabled={false}
      onPlanModeChange={onPlanModeChange}
      reasoningLevel="medium"
      onReasoningLevelChange={onReasoningLevelChange}
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

    fireEvent.change(screen.getByPlaceholderText('Message GOAT AI'), {
      target: { value: 'Hello there' },
    })

    expect(sendButton).toBeEnabled()
  })

  it('renders composer model and reasoning menu triggers', () => {
    renderChatWindow()

    expect(screen.getByRole('button', { name: /open model menu/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /open reasoning menu/i })).toBeInTheDocument()
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

  it('keeps upload, manage uploads, and plan mode inside the plus popover', () => {
    renderChatWindow()

    fireEvent.click(screen.getByTitle(/open upload and planning actions/i))

    expect(screen.getByText('Upload Files')).toBeInTheDocument()
    expect(screen.getByText('Manage Uploads')).toBeInTheDocument()
    expect(screen.getByText('Plan Mode')).toBeInTheDocument()
  })

  it('shows a compact blue plan indicator beside reasoning only when plan mode is enabled', () => {
    renderChatWindow()
    expect(screen.queryByLabelText(/plan enabled/i)).not.toBeInTheDocument()

    renderChatWindow({ planModeEnabled: true })
    expect(screen.getByLabelText(/plan enabled/i)).toBeInTheDocument()
    expect(screen.getByText('Plan')).toBeInTheDocument()
  })

  it('keeps plan mode switch wired while the blue indicator order is stable', () => {
    const { onPlanModeChange } = renderChatWindow({ planModeEnabled: true })

    fireEvent.click(screen.getByTitle(/open upload and planning actions/i))
    fireEvent.click(screen.getByRole('switch'))

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
})
