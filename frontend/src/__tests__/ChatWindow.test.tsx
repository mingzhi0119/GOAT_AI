import { fireEvent, render, screen, waitFor } from '@testing-library/react'
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

function renderChatWindow() {
  return render(
    <ChatWindow
      messages={[]}
      chartSpec={null}
      isStreaming={false}
      selectedModel="test-model"
      supportsVision
      fileContext={null}
      onUploadEvent={vi.fn()}
      onSendMessage={vi.fn()}
      onSetFileContextMode={vi.fn()}
      onStop={vi.fn()}
      onClearFileContext={vi.fn()}
      gpuStatus={baseGpuStatus}
      gpuError={null}
      inferenceLatency={baseLatency}
    />,
  )
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
