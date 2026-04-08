import { Suspense, lazy, useEffect, useMemo, useRef, useState, type FC, type KeyboardEvent } from 'react'
import { uploadMediaImage } from '../api/media'
import type { ChartSpec, Message } from '../api/types'
import type { GPUStatus, InferenceLatency } from '../api/system'
import type { FileContext } from '../hooks/useFileContext'
import { getSuffixPrompt, getTemplateFallbackPrompt } from '../utils/uploadPrompts'
import GpuStatusDot from './GpuStatusDot'
import MessageBubble from './MessageBubble'

const LazyChartCard = lazy(() => import('./ChartCard'))

const BASE_PROMPTS = [
  'Summarize key trends in consumer behavior',
  'What are the top strategic risks for 2026?',
  "Explain Porter's Five Forces briefly",
  'Draft an executive summary template',
]

type PromptItem =
  | { text: string; kind: 'base' }
  | { text: string; kind: 'suffix' }
  | { text: string; kind: 'template' }

interface Props {
  messages: Message[]
  chartSpec: ChartSpec | null
  isStreaming: boolean
  selectedModel: string
  /** When true, show image attach control (model reports Ollama ``vision`` capability). */
  supportsVision?: boolean
  fileContext: FileContext | null
  onSendMessage: (content: string, imageAttachmentIds?: string[]) => void
  onStop: () => void
  gpuStatus: GPUStatus | null
  gpuError: string | null
  inferenceLatency: InferenceLatency | null
}

/** Main chat panel: message list + auto-scroll + input area. */
const ChatWindow: FC<Props> = ({
  messages,
  chartSpec,
  isStreaming,
  selectedModel,
  supportsVision = false,
  fileContext,
  onSendMessage,
  onStop,
  gpuStatus,
  gpuError,
  inferenceLatency,
}) => {
  const [input, setInput] = useState('')
  const [pendingImageIds, setPendingImageIds] = useState<string[]>([])
  const [imageUploadError, setImageUploadError] = useState<string | null>(null)
  const [imageUploading, setImageUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const starterPrompts = useMemo<PromptItem[]>(() => {
    if (!fileContext) {
      return BASE_PROMPTS.map((text: string): PromptItem => ({ text, kind: 'base' }))
    }
    const filename = fileContext.filename
    return [
      { text: BASE_PROMPTS[0]!, kind: 'base' },
      { text: BASE_PROMPTS[1]!, kind: 'base' },
      {
        text: fileContext.suffixPrompt ?? getSuffixPrompt(filename),
        kind: 'suffix',
      },
      {
        text: fileContext.templatePrompt ?? getTemplateFallbackPrompt(filename),
        kind: 'template',
      },
    ]
  }, [fileContext])

  /** Visible (non-hidden) messages to render in the chat list. */
  const visibleMessages = useMemo(() => messages.filter(m => !m.hidden), [messages])

  /**
   * True when the current session has an active file upload OR carries embedded
   * legacy hidden messages (restored from history). Used to enable chart
   * block stripping in MessageBubble.
   */
  const sessionHasFileContext = fileContext !== null || messages.some(m => m.hidden)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSubmit = () => {
    const trimmed = input.trim()
    if ((!trimmed && !pendingImageIds.length) || isStreaming) return
    const text =
      trimmed || (pendingImageIds.length > 0 ? 'What do you see in this image?' : '')
    onSendMessage(text, pendingImageIds.length > 0 ? pendingImageIds : undefined)
    setInput('')
    setPendingImageIds([])
    setImageUploadError(null)
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }

  const handleImagePick = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files?.length) return
    setImageUploadError(null)
    setImageUploading(true)
    try {
      const next: string[] = [...pendingImageIds]
      for (const f of Array.from(files)) {
        const res = await uploadMediaImage(f)
        next.push(res.attachment_id)
      }
      setPendingImageIds(next)
    } catch (err) {
      setImageUploadError(err instanceof Error ? err.message : 'Image upload failed')
    } finally {
      setImageUploading(false)
      e.target.value = ''
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)
    e.target.style.height = 'auto'
    e.target.style.height = `${Math.min(e.target.scrollHeight, 180)}px`
  }

  const canSend = (input.trim().length > 0 || pendingImageIds.length > 0) && !isStreaming

  return (
    <div
      className="flex flex-col flex-1 min-w-0 min-h-0 h-full"
      style={{ background: 'var(--bg-chat)' }}
    >
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
        {chartSpec && visibleMessages.length > 0 && (
          <Suspense
            fallback={
              <div
                className="rounded-2xl p-4 border text-sm"
                style={{
                  borderColor: 'var(--border-color)',
                  background: 'var(--bg-asst-bubble)',
                  color: 'var(--text-muted)',
                }}
              >
                Loading chart...
              </div>
            }
          >
            <LazyChartCard spec={chartSpec} />
          </Suspense>
        )}
        {visibleMessages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-5 text-center px-4">
            <div
              className="w-20 h-20 rounded-2xl overflow-hidden"
              style={{
                border: '1.5px solid #FFCD00',
                background: '#2b2b2b',
              }}
            >
              <img
                src="./golden_goat_icon.png"
                alt="GOAT AI"
                style={{ width: '100%', height: '100%', objectFit: 'cover' }}
              />
            </div>
            <div>
              <h2 className="text-xl font-bold mb-1" style={{ color: 'var(--text-main)' }}>
                Welcome to GOAT AI
              </h2>
              <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
                Strategic Intelligence - Simon Business School
              </p>
              {selectedModel && (
                <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
                  Model: <span style={{ color: 'var(--gold)' }}>{selectedModel}</span>
                  {supportsVision && (
                    <span className="ml-2" title="This model reports vision support in Ollama">
                      · vision
                    </span>
                  )}
                </p>
              )}
            </div>
            <div className="grid grid-cols-2 gap-2 w-full max-w-md mt-2">
              {starterPrompts.map((item, i) => {
                const isFilePrompt = item.kind !== 'base'
                return (
                  <button
                    key={`${item.kind}-${i}-${item.text}`}
                    onClick={() => onSendMessage(item.text, undefined)}
                    className="text-xs px-3 py-2 rounded-xl text-left transition-colors hover:opacity-80"
                    style={{
                      border: isFilePrompt
                        ? '1px solid var(--gold)'
                        : '1px solid var(--border-color)',
                      color: 'var(--text-main)',
                      background: isFilePrompt
                        ? 'rgba(255,205,0,0.08)'
                        : 'var(--bg-asst-bubble)',
                    }}
                  >
                    {isFilePrompt && (
                      <span
                        className="block text-[10px] font-semibold mb-0.5 leading-none"
                        style={{ color: 'var(--gold)' }}
                      >
                        {item.kind === 'suffix' ? 'From your file' : 'Template suggestion'}
                      </span>
                    )}
                    {item.text}
                  </button>
                )
              })}
            </div>
          </div>
        ) : (
          visibleMessages.map(msg => (
            <MessageBubble key={msg.id} message={msg} hasFileContext={sessionHasFileContext} />
          ))
        )}
        <div ref={bottomRef} />
      </div>

      <div
        className="flex-shrink-0 px-4 py-3 border-t"
        style={{ borderColor: 'var(--border-color)', background: 'var(--bg-chat)' }}
      >
        <div className="flex items-center gap-2 max-w-4xl mx-auto">
          <input
            ref={fileInputRef}
            type="file"
            accept="image/png,image/jpeg,image/jpg,image/webp"
            multiple
            className="hidden"
            onChange={handleImagePick}
          />
          {supportsVision && (
            <button
              type="button"
              disabled={isStreaming || imageUploading}
              onClick={() => fileInputRef.current?.click()}
              className="flex-shrink-0 px-2 py-2 rounded-xl text-lg leading-none disabled:opacity-40"
              style={{
                border: '1px solid var(--border-color)',
                color: 'var(--text-muted)',
                background: 'var(--bg-asst-bubble)',
              }}
              title="Attach images (PNG, JPEG, WebP)"
            >
              {imageUploading ? '...' : '📸'}
            </button>
          )}
          <GpuStatusDot
            gpuStatus={gpuStatus}
            gpuError={gpuError}
            inferenceLatency={inferenceLatency}
          />
          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            placeholder="Message GOAT AI (Enter to send, Shift+Enter for newline)"
            rows={1}
            disabled={isStreaming}
            className="flex-1 resize-none rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 transition-all"
            style={{
              background: 'var(--input-bg)',
              border: '1px solid var(--input-border)',
              color: 'var(--text-main)',
              lineHeight: '1.5',
              maxHeight: '180px',
            }}
          />
          <button
            type="button"
            onClick={isStreaming ? onStop : handleSubmit}
            disabled={!isStreaming && !canSend}
            className="flex-shrink-0 px-5 py-2.5 rounded-xl text-sm font-semibold transition-all disabled:opacity-40"
            style={{
              background: isStreaming ? '#dc2626' : canSend ? 'var(--navy)' : 'var(--border-color)',
              color: isStreaming || canSend ? '#fff' : 'var(--text-muted)',
            }}
          >
            {isStreaming ? 'Stop' : 'Send'}
          </button>
        </div>
        {pendingImageIds.length > 0 && (
          <div className="max-w-4xl mx-auto flex flex-wrap gap-1.5 mt-2 justify-center">
            {pendingImageIds.map((id, i) => (
              <button
                key={`${id}-${i}`}
                type="button"
                onClick={() => setPendingImageIds(prev => prev.filter((_, j) => j !== i))}
                className="text-[10px] px-2 py-0.5 rounded-lg"
                style={{
                  border: '1px solid var(--border-color)',
                  color: 'var(--text-muted)',
                  background: 'var(--bg-asst-bubble)',
                }}
                title="Remove"
              >
                Image {i + 1} ×
              </button>
            ))}
          </div>
        )}
        {imageUploadError && (
          <p className="text-center text-xs mt-1 text-red-600">{imageUploadError}</p>
        )}
        <p className="text-center text-xs mt-1.5" style={{ color: 'var(--text-muted)' }}>
          AI may make mistakes. Verify important information.
        </p>
      </div>
    </div>
  )
}

export default ChatWindow
