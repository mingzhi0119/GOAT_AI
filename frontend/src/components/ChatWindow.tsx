import { Suspense, lazy, useEffect, useMemo, useRef, useState, type FC, type KeyboardEvent } from 'react'
import { uploadMediaImage } from '../api/media'
import { streamUpload, type UploadStreamEvent } from '../api/upload'
import type { GPUStatus, InferenceLatency } from '../api/system'
import type { ChartSpec, Message } from '../api/types'
import type { FileContext } from '../hooks/useFileContext'
import {
  getFileExtension,
  getSuffixPrompt,
  getTemplateFallbackPrompt,
} from '../utils/uploadPrompts'
import GpuStatusDot from './GpuStatusDot'
import MessageBubble from './MessageBubble'

const LazyChartCard = lazy(() => import('./ChartCard'))

const BASE_PROMPTS = [
  'Summarize key trends in consumer behavior',
  'What are the top strategic risks for 2026?',
  "Explain Porter's Five Forces briefly",
  'Draft an executive summary template',
]

const KNOWLEDGE_FILE_EXTENSIONS = new Set(['csv', 'xlsx', 'pdf', 'docx', 'md', 'txt'])
const IMAGE_FILE_EXTENSIONS = new Set(['png', 'jpg', 'jpeg', 'webp'])
const TEXTAREA_MAX_HEIGHT_PX = 144
const TEXTAREA_MIN_HEIGHT_PX = 44

type PromptItem =
  | { text: string; kind: 'base' }
  | { text: string; kind: 'suffix' }
  | { text: string; kind: 'template' }

interface Props {
  messages: Message[]
  chartSpec: ChartSpec | null
  isStreaming: boolean
  selectedModel: string
  supportsVision?: boolean
  fileContext: FileContext | null
  onUploadEvent: (event: UploadStreamEvent) => void
  onSendMessage: (content: string, imageAttachmentIds?: string[]) => void
  onSetFileContextMode: (mode: 'idle' | 'single' | 'persistent') => void
  onStop: () => void
  onClearFileContext: () => void
  gpuStatus: GPUStatus | null
  gpuError: string | null
  inferenceLatency: InferenceLatency | null
}

const PlusIcon = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
    <path
      d="M8 3.25v9.5M3.25 8h9.5"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
    />
  </svg>
)

const CloseIcon = () => (
  <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
    <path
      d="M3 3l6 6M9 3 3 9"
      stroke="currentColor"
      strokeWidth="1.4"
      strokeLinecap="round"
    />
  </svg>
)

const SendArrowIcon = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
    <path
      d="M8 12.75V4.5M8 4.5l-3.25 3.25M8 4.5l3.25 3.25"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
)

const StopIcon = () => (
  <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
    <rect x="3.25" y="3.25" width="7.5" height="7.5" rx="1.5" fill="currentColor" />
  </svg>
)

function getAttachmentKind(file: File, supportsVision: boolean): 'image' | 'knowledge' | 'unsupported' {
  const ext = getFileExtension(file.name)
  if (KNOWLEDGE_FILE_EXTENSIONS.has(ext)) return 'knowledge'
  if (supportsVision && IMAGE_FILE_EXTENSIONS.has(ext)) return 'image'
  return 'unsupported'
}

function supportedAttachmentLabel(supportsVision: boolean): string {
  return supportsVision
    ? 'PNG, JPG, WEBP, CSV, XLSX, PDF, DOCX, MD, or TXT'
    : 'CSV, XLSX, PDF, DOCX, MD, or TXT'
}

function formatAttachmentErrorMessage(error: unknown, supportsVision: boolean): string {
  const fallback = 'Attachment upload failed'
  const message = error instanceof Error ? error.message : fallback
  if (message.startsWith('Unsupported file type:')) {
    return `Unsupported file type. Please upload a ${supportedAttachmentLabel(supportsVision)} file.`
  }
  return message
}

const ChatWindow: FC<Props> = ({
  messages,
  chartSpec,
  isStreaming,
  selectedModel,
  supportsVision = false,
  fileContext,
  onUploadEvent,
  onSendMessage,
  onSetFileContextMode,
  onStop,
  onClearFileContext,
  gpuStatus,
  gpuError,
  inferenceLatency,
}) => {
  const [input, setInput] = useState('')
  const [pendingImageIds, setPendingImageIds] = useState<string[]>([])
  const [attachmentUploadError, setAttachmentUploadError] = useState<string | null>(null)
  const [attachmentUploading, setAttachmentUploading] = useState(false)
  const [attachmentStatus, setAttachmentStatus] = useState<string | null>(null)
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
      { text: fileContext.suffixPrompt ?? getSuffixPrompt(filename), kind: 'suffix' },
      { text: fileContext.templatePrompt ?? getTemplateFallbackPrompt(filename), kind: 'template' },
    ]
  }, [fileContext])

  const visibleMessages = useMemo(() => messages.filter(message => !message.hidden), [messages])
  const sessionHasFileContext = fileContext !== null || messages.some(message => message.hidden)
  const attachmentAccept = supportsVision
    ? 'image/png,image/jpeg,image/jpg,image/webp,.csv,.xlsx,.pdf,.docx,.md,.txt'
    : '.csv,.xlsx,.pdf,.docx,.md,.txt'

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    const textarea = textareaRef.current
    if (!textarea) return
    textarea.style.height = 'auto'
    const hasContent = input.trim().length > 0
    const nextHeight = hasContent
      ? Math.min(textarea.scrollHeight, TEXTAREA_MAX_HEIGHT_PX)
      : TEXTAREA_MIN_HEIGHT_PX
    textarea.style.height = `${Math.max(TEXTAREA_MIN_HEIGHT_PX, nextHeight)}px`
    textarea.style.overflowY = textarea.scrollHeight > TEXTAREA_MAX_HEIGHT_PX ? 'auto' : 'hidden'
  }, [input])

  const handleSubmit = () => {
    const trimmed = input.trim()
    if ((!trimmed && !pendingImageIds.length) || isStreaming || attachmentUploading) return
    const text = trimmed || (pendingImageIds.length > 0 ? 'What do you see in this image?' : '')
    onSendMessage(text, pendingImageIds.length > 0 ? pendingImageIds : undefined)
    setInput('')
    setPendingImageIds([])
    setAttachmentUploadError(null)
    setAttachmentStatus(null)
  }

  const uploadKnowledgeFile = async (file: File) => {
    setAttachmentStatus(`Analyzing ${file.name}...`)
    for await (const event of streamUpload(file)) {
      if (event.type === 'file_prompt' || event.type === 'knowledge_ready') {
        onUploadEvent(event)
      } else if (event.type === 'error') {
        throw new Error(event.message)
      }
    }
    setAttachmentStatus(`${file.name} ready`)
  }

  const handleAttachmentPick = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files ? Array.from(e.target.files) : []
    e.target.value = ''
    if (files.length === 0) return

    setAttachmentUploadError(null)
    setAttachmentUploading(true)
    try {
      const knowledgeFiles = files.filter(
        file => getAttachmentKind(file, supportsVision) === 'knowledge',
      )
      const imageFiles = files.filter(file => getAttachmentKind(file, supportsVision) === 'image')
      const unsupportedFiles = files.filter(
        file => getAttachmentKind(file, supportsVision) === 'unsupported',
      )

      if (unsupportedFiles.length > 0) {
        throw new Error(`Unsupported file type: ${unsupportedFiles[0]!.name}`)
      }
      if (knowledgeFiles.length > 1) {
        throw new Error('Please upload one knowledge file at a time.')
      }

      for (const imageFile of imageFiles) {
        setAttachmentStatus(`Uploading ${imageFile.name}...`)
        const result = await uploadMediaImage(imageFile)
        setPendingImageIds(prev => [...prev, result.attachment_id])
      }

      const knowledgeFile = knowledgeFiles[0]
      if (knowledgeFile) {
        await uploadKnowledgeFile(knowledgeFile)
      } else if (imageFiles.length > 0) {
        setAttachmentStatus(`${imageFiles.length} image attachment${imageFiles.length > 1 ? 's' : ''} ready`)
      } else {
        setAttachmentStatus(null)
      }
    } catch (err) {
      setAttachmentStatus(null)
      setAttachmentUploadError(formatAttachmentErrorMessage(err, supportsVision))
    } finally {
      setAttachmentUploading(false)
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const canSend =
    (input.trim().length > 0 || pendingImageIds.length > 0) && !isStreaming && !attachmentUploading

  return (
    <div
      className="flex h-full min-h-0 min-w-0 flex-1 flex-col"
      style={{ background: 'var(--bg-chat)' }}
    >
      <div className="flex-1 space-y-4 overflow-y-auto px-4 py-6">
        {chartSpec && visibleMessages.length > 0 && (
          <Suspense
            fallback={
              <div
                className="rounded-2xl border p-4 text-sm"
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
          <div className="flex h-full flex-col items-center justify-center gap-5 px-4 text-center">
            <div
              className="h-20 w-20 overflow-hidden rounded-2xl"
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
              <h2 className="mb-1 text-xl font-bold" style={{ color: 'var(--text-main)' }}>
                Welcome to GOAT AI
              </h2>
              <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
                Strategic Intelligence - Simon Business School
              </p>
              {selectedModel && (
                <p className="mt-1 text-xs" style={{ color: 'var(--text-muted)' }}>
                  Model: <span style={{ color: 'var(--gold)' }}>{selectedModel}</span>
                  {supportsVision && (
                    <span className="ml-2" title="This model reports vision support in Ollama">
                      vision
                    </span>
                  )}
                </p>
              )}
            </div>
            <div className="mt-2 grid w-full max-w-md grid-cols-2 gap-2">
              {starterPrompts.map((item, index) => {
                const isFilePrompt = item.kind !== 'base'
                return (
                  <button
                    key={`${item.kind}-${index}-${item.text}`}
                    onClick={() => onSendMessage(item.text, undefined)}
                    className="rounded-xl px-3 py-2 text-left text-xs transition-colors hover:opacity-80"
                    style={{
                      border: isFilePrompt
                        ? '1px solid var(--gold)'
                        : '1px solid var(--border-color)',
                      color: 'var(--text-main)',
                      background: isFilePrompt ? 'rgba(255,205,0,0.08)' : 'var(--bg-asst-bubble)',
                    }}
                  >
                    {isFilePrompt && (
                      <span
                        className="mb-0.5 block text-[10px] font-semibold leading-none"
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
          visibleMessages.map(message => (
            <MessageBubble
              key={message.id}
              message={message}
              hasFileContext={sessionHasFileContext}
            />
          ))
        )}
        <div ref={bottomRef} />
      </div>

      <div
        className="flex-shrink-0 border-t px-4 py-3"
        style={{ borderColor: 'var(--border-color)', background: 'var(--bg-chat)' }}
      >
        <div className="mx-auto max-w-4xl space-y-2">
          {(fileContext || pendingImageIds.length > 0 || attachmentStatus) && (
            <div className="flex flex-wrap items-center gap-2 px-1">
              {fileContext && (
                <div
                  className="inline-flex items-center gap-2 rounded-2xl border px-3 py-1.5 text-xs"
                  style={{
                    borderColor: 'rgba(255,255,255,0.12)',
                    background: 'rgba(255,255,255,0.05)',
                    color: 'var(--text-main)',
                  }}
                >
                  <span className="max-w-[220px] truncate">{fileContext.filename}</span>
                  <div
                    className="inline-flex items-center overflow-hidden rounded-full border"
                    style={{
                      borderColor: 'rgba(255,255,255,0.12)',
                      background: 'rgba(255,255,255,0.03)',
                    }}
                  >
                    <button
                      type="button"
                      onClick={() => onSetFileContextMode('single')}
                      className="px-2.5 py-1 text-[11px] transition-colors"
                      style={{
                        background:
                          fileContext.bindingMode === 'single'
                            ? 'rgba(255,255,255,0.12)'
                            : 'transparent',
                        color:
                          fileContext.bindingMode === 'single'
                            ? 'var(--text-main)'
                            : 'var(--text-muted)',
                      }}
                      title="Use this document for the next message only"
                    >
                      Next Turn
                    </button>
                    <button
                      type="button"
                      onClick={() => onSetFileContextMode('persistent')}
                      className="border-l px-2.5 py-1 text-[11px] transition-colors"
                      style={{
                        borderColor: 'rgba(255,255,255,0.12)',
                        background:
                          fileContext.bindingMode === 'persistent'
                            ? 'rgba(255,255,255,0.12)'
                            : 'transparent',
                        color:
                          fileContext.bindingMode === 'persistent'
                            ? 'var(--text-main)'
                            : 'var(--text-muted)',
                      }}
                      title="Keep using this document until cleared"
                    >
                      Sticky
                    </button>
                    <button
                      type="button"
                      onClick={() => onSetFileContextMode('idle')}
                      className="border-l px-2.5 py-1 text-[11px] transition-colors"
                      style={{
                        borderColor: 'rgba(255,255,255,0.12)',
                        background:
                          fileContext.bindingMode === 'idle'
                            ? 'rgba(255,255,255,0.1)'
                            : 'transparent',
                        color:
                          fileContext.bindingMode === 'idle'
                            ? 'var(--text-main)'
                            : 'var(--text-muted)',
                      }}
                      title="Keep the document available but do not attach it automatically"
                    >
                      Inactive
                    </button>
                  </div>
                  <button
                    type="button"
                    onClick={onClearFileContext}
                    className="flex h-4 w-4 items-center justify-center rounded-full"
                    style={{ color: 'var(--text-muted)' }}
                    title="Clear file context"
                  >
                    <CloseIcon />
                  </button>
                </div>
              )}
              {pendingImageIds.map((id, index) => (
                <button
                  key={`${id}-${index}`}
                  type="button"
                  onClick={() => setPendingImageIds(prev => prev.filter((_, i) => i !== index))}
                  className="inline-flex items-center gap-2 rounded-2xl border px-3 py-1.5 text-xs"
                  style={{
                    borderColor: 'rgba(255,255,255,0.12)',
                    background: 'rgba(255,255,255,0.05)',
                    color: 'var(--text-muted)',
                  }}
                  title="Remove image attachment"
                >
                  <span>Image {index + 1}</span>
                  <CloseIcon />
                </button>
              ))}
              {attachmentStatus && (
                <div
                  className="rounded-2xl border px-3 py-1.5 text-xs"
                  style={{
                    borderColor: 'rgba(255,255,255,0.14)',
                    background: 'rgba(255,255,255,0.05)',
                    color: 'var(--text-muted)',
                  }}
                >
                  {attachmentStatus}
                </div>
              )}
            </div>
          )}

          <div
            className="rounded-[26px] border px-4 py-2.5 shadow-[0_18px_40px_rgba(0,0,0,0.18)]"
            style={{
              borderColor: 'rgba(255,255,255,0.09)',
              background:
                'linear-gradient(180deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.02) 100%)',
            }}
          >
            <div className="flex flex-col gap-2.5">
              <input
                ref={fileInputRef}
                type="file"
                accept={attachmentAccept}
                multiple
                className="hidden"
                onChange={handleAttachmentPick}
              />

              <div className="min-w-0">
                <textarea
                  ref={textareaRef}
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Message GOAT AI"
                  rows={1}
                  disabled={isStreaming}
                  className="w-full resize-none bg-transparent px-0 py-0 text-sm focus:outline-none"
                  style={{
                    color: 'var(--text-main)',
                    lineHeight: '22px',
                    minHeight: `${TEXTAREA_MIN_HEIGHT_PX}px`,
                    maxHeight: `${TEXTAREA_MAX_HEIGHT_PX}px`,
                  }}
                />
              </div>

              <div className="flex items-center justify-between gap-3">
                <div className="flex min-w-0 flex-1 items-center">
                  <button
                    type="button"
                    disabled={isStreaming || attachmentUploading}
                    onClick={() => fileInputRef.current?.click()}
                    className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full transition-all disabled:opacity-40 hover:opacity-80"
                    style={{
                      border: '1px solid rgba(255,255,255,0.14)',
                      color: 'var(--text-main)',
                      background:
                        'linear-gradient(180deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0.04) 100%)',
                    }}
                    title={
                      supportsVision ? 'Attach images or knowledge files' : 'Attach a knowledge file'
                    }
                  >
                    <PlusIcon />
                  </button>
                </div>

                <div className="flex flex-shrink-0 items-center gap-2">
                  <GpuStatusDot
                    gpuStatus={gpuStatus}
                    gpuError={gpuError}
                    inferenceLatency={inferenceLatency}
                  />
                  <button
                    type="button"
                    onClick={isStreaming ? onStop : handleSubmit}
                    disabled={!isStreaming && !canSend}
                    aria-label={isStreaming ? 'Stop generating' : 'Send message'}
                    className="flex h-10 w-10 items-center justify-center rounded-full transition-all disabled:cursor-not-allowed"
                    style={{
                      background: isStreaming
                        ? '#111111'
                        : canSend
                          ? '#111111'
                          : 'rgba(255,255,255,0.16)',
                      color: isStreaming || canSend ? '#ffffff' : 'rgba(255,255,255,0.5)',
                    }}
                    title={isStreaming ? 'Stop generating' : 'Send message'}
                  >
                    {isStreaming ? <StopIcon /> : <SendArrowIcon />}
                  </button>
                </div>
              </div>
            </div>
          </div>

          {attachmentUploadError && (
            <div
              role="status"
              aria-live="polite"
              className="mt-2 rounded-2xl border px-3 py-2 text-sm"
              style={{
                borderColor: 'rgba(239,68,68,0.28)',
                background: 'rgba(239,68,68,0.08)',
                color: '#fca5a5',
              }}
            >
              {attachmentUploadError}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default ChatWindow
