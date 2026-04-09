import {
  Suspense,
  lazy,
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type ReactNode,
  type FC,
  type KeyboardEvent,
} from 'react'
import { uploadMediaImage } from '../api/media'
import { streamUpload, type UploadStreamEvent } from '../api/upload'
import type { GPUStatus, InferenceLatency } from '../api/system'
import type { ChartSpec, Message } from '../api/types'
import type { FileBindingMode, FileContextItem } from '../hooks/useFileContext'
import {
  getFileExtension,
  getSuffixPrompt,
  getTemplateFallbackPrompt,
} from '../utils/uploadPrompts'
import type { ChatLayoutDecisions } from '../utils/chatLayout'
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
const TEXTAREA_MIN_HEIGHT_PX = 28

type PromptItem =
  | { text: string; kind: 'base' }
  | { text: string; kind: 'suffix' }
  | { text: string; kind: 'template' }

interface PendingImageAttachment {
  id: string
  filename: string
}

type ComposerPanel = 'plus' | 'manage-uploads' | 'model' | 'reasoning' | null
type ComposerIndicatorKey = 'plan'

interface ComposerIndicatorDescriptor {
  key: ComposerIndicatorKey
  visible: boolean
  label: string
  icon: ReactNode
  tooltip: string
  onClick?: () => void
}

interface Props {
  messages: Message[]
  chartSpec: ChartSpec | null
  isStreaming: boolean
  layoutDecisions: ChatLayoutDecisions
  models: string[]
  selectedModel: string
  onModelChange: (model: string) => void
  supportsVision?: boolean
  fileContexts: FileContextItem[]
  activeFileContext: FileContextItem | null
  onUploadEvent: (event: UploadStreamEvent) => void
  onSendMessage: (content: string, imageAttachmentIds?: string[]) => void
  onSetFileContextMode: (id: string, mode: FileBindingMode) => void
  onRemoveFileContext: (id: string) => void
  onStop: () => void
  gpuStatus: GPUStatus | null
  gpuError: string | null
  inferenceLatency: InferenceLatency | null
  planModeEnabled: boolean
  onPlanModeChange: (enabled: boolean) => void
  reasoningLevel: 'low' | 'medium' | 'high'
  onReasoningLevelChange: (level: 'low' | 'medium' | 'high') => void
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
  <svg width="24" height="24" viewBox="0 0 20 20" fill="none" aria-hidden="true">
    <path
      d="M10 15.25V4.75M10 4.75 5.9 8.85M10 4.75l4.1 4.1"
      stroke="currentColor"
      strokeWidth="2.15"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
)

const StopIcon = () => (
  <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
    <rect x="4" y="4" width="10" height="10" rx="2" fill="currentColor" />
  </svg>
)

const UploadIcon = () => (
  <svg width="15" height="15" viewBox="0 0 16 16" fill="none" aria-hidden="true">
    <path
      d="M8 10.75V3.75M8 3.75 5.5 6.25M8 3.75l2.5 2.5M3.75 10.5v1.25c0 .28.22.5.5.5h7.5c.28 0 .5-.22.5-.5V10.5"
      stroke="currentColor"
      strokeWidth="1.4"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
)

const ManageIcon = () => (
  <svg width="15" height="15" viewBox="0 0 16 16" fill="none" aria-hidden="true">
    <path
      d="M3 4.25h10M3 8h10M3 11.75h6"
      stroke="currentColor"
      strokeWidth="1.4"
      strokeLinecap="round"
    />
  </svg>
)

const PlanModeIcon = () => (
  <svg width="15" height="15" viewBox="0 0 16 16" fill="none" aria-hidden="true">
    <path
      d="M4 3.75h8M4 8h5.5M4 12.25h6.5"
      stroke="currentColor"
      strokeWidth="1.45"
      strokeLinecap="round"
    />
    <circle cx="11.75" cy="8" r="1.25" fill="currentColor" />
  </svg>
)

const ChevronRightIcon = () => (
  <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
    <path
      d="M5.25 3.5 8.75 7l-3.5 3.5"
      stroke="currentColor"
      strokeWidth="1.4"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
)

const ChevronDownIcon = () => (
  <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
    <path
      d="M3 4.5 6 7.5l3-3"
      stroke="currentColor"
      strokeWidth="1.35"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
)

const CheckIcon = () => (
  <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
    <path
      d="M3.5 7.3 5.8 9.6l4.7-4.9"
      stroke="currentColor"
      strokeWidth="1.45"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
)

const DocumentIcon = () => (
  <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">
    <path
      d="M5 2.75h4.5L12.25 5.5V12.25a1 1 0 0 1-1 1h-6.5a1 1 0 0 1-1-1v-8.5a1 1 0 0 1 1-1Z"
      stroke="currentColor"
      strokeWidth="1.3"
      strokeLinejoin="round"
    />
    <path d="M9.5 2.75V5.5h2.75" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
  </svg>
)

const ImageIcon = () => (
  <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">
    <rect x="2.5" y="3" width="11" height="10" rx="2" stroke="currentColor" strokeWidth="1.3" />
    <circle cx="6" cy="6.5" r="1" fill="currentColor" />
    <path
      d="M4 11l2.5-2.5 1.75 1.75L10.5 8 12 9.5"
      stroke="currentColor"
      strokeWidth="1.2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
)

const ProcessingDot = () => (
  <span className="inline-flex h-2 w-2 rounded-full bg-amber-400/80" aria-hidden="true" />
)

const ReadyDot = () => (
  <span className="inline-flex h-2 w-2 rounded-full bg-emerald-400/80" aria-hidden="true" />
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

function modeLabel(mode: FileBindingMode): string {
  if (mode === 'single') return 'Next'
  if (mode === 'persistent') return 'Sticky'
  return 'Off'
}

function reasoningLabel(level: 'low' | 'medium' | 'high'): string {
  if (level === 'low') return 'Low'
  if (level === 'high') return 'High'
  return 'Medium'
}

function getComposerIndicators(
  planModeEnabled: boolean,
  onPlanModeChange: (enabled: boolean) => void,
): Array<Omit<ComposerIndicatorDescriptor, 'visible'>> {
  const orderedIndicators: ComposerIndicatorDescriptor[] = [
    {
      key: 'plan',
      visible: planModeEnabled,
      label: 'Plan',
      icon: <PlanModeIcon />,
      tooltip: 'Planning mode is enabled.',
      onClick: () => onPlanModeChange(false),
    },
  ]

  return orderedIndicators
    .filter(indicator => indicator.visible)
    .map(({ key, label, icon, tooltip, onClick }) => ({ key, label, icon, tooltip, onClick }))
}

function handleComposerTextAreaPointerDown(
  event: React.MouseEvent<HTMLDivElement>,
  textarea: HTMLTextAreaElement | null,
  closePanel: () => void,
): void {
  closePanel()
  if (event.target !== textarea && textarea) {
    event.preventDefault()
    textarea.focus()
  }
}

const ChatWindow: FC<Props> = ({
  messages,
  chartSpec,
  isStreaming,
  layoutDecisions,
  models,
  selectedModel,
  onModelChange,
  supportsVision = false,
  fileContexts,
  activeFileContext,
  onUploadEvent,
  onSendMessage,
  onSetFileContextMode,
  onRemoveFileContext,
  onStop,
  gpuStatus,
  gpuError,
  inferenceLatency,
  planModeEnabled,
  onPlanModeChange,
  reasoningLevel,
  onReasoningLevelChange,
}) => {
  const [input, setInput] = useState('')
  const [pendingImages, setPendingImages] = useState<PendingImageAttachment[]>([])
  const [attachmentUploadError, setAttachmentUploadError] = useState<string | null>(null)
  const [attachmentUploading, setAttachmentUploading] = useState(false)
  const [activePanel, setActivePanel] = useState<ComposerPanel>(null)
  const [hoveredIndicator, setHoveredIndicator] = useState<ComposerIndicatorKey | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const composerRef = useRef<HTMLDivElement>(null)
  const panelBoundaryRef = useRef<HTMLDivElement>(null)

  const starterPrompts = useMemo<PromptItem[]>(() => {
    if (!activeFileContext) {
      return BASE_PROMPTS.map((text: string): PromptItem => ({ text, kind: 'base' }))
    }
    const filename = activeFileContext.filename
    return [
      { text: BASE_PROMPTS[0]!, kind: 'base' },
      { text: BASE_PROMPTS[1]!, kind: 'base' },
      { text: activeFileContext.suffixPrompt ?? getSuffixPrompt(filename), kind: 'suffix' },
      {
        text: activeFileContext.templatePrompt ?? getTemplateFallbackPrompt(filename),
        kind: 'template',
      },
    ]
  }, [activeFileContext])

  const visibleMessages = useMemo(() => messages.filter(message => !message.hidden), [messages])
  const sessionHasFileContext = fileContexts.length > 0 || messages.some(message => message.hidden)
  const uploadedKnowledgeFiles = useMemo(
    () => fileContexts.filter(item => item.documentId || item.status === 'processing'),
    [fileContexts],
  )
  const attachmentAccept = supportsVision
    ? 'image/png,image/jpeg,image/jpg,image/webp,.csv,.xlsx,.pdf,.docx,.md,.txt'
    : '.csv,.xlsx,.pdf,.docx,.md,.txt'

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    const handlePointerDown = (event: PointerEvent) => {
      if (!activePanel) return
      if (!panelBoundaryRef.current?.contains(event.target as Node)) {
        setActivePanel(null)
      }
    }

    document.addEventListener('pointerdown', handlePointerDown)
    return () => document.removeEventListener('pointerdown', handlePointerDown)
  }, [activePanel])

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
    const pendingImageIds = pendingImages.map(item => item.id)
    if ((!trimmed && !pendingImageIds.length) || isStreaming || attachmentUploading) return
    const text = trimmed || (pendingImageIds.length > 0 ? 'What do you see in this image?' : '')
    onSendMessage(text, pendingImageIds.length > 0 ? pendingImageIds : undefined)
    setInput('')
    setPendingImages([])
    setAttachmentUploadError(null)
    setActivePanel(null)
  }

  const uploadKnowledgeFile = async (file: File) => {
    for await (const event of streamUpload(file)) {
      if (event.type === 'file_prompt' || event.type === 'knowledge_ready') {
        onUploadEvent(event)
      } else if (event.type === 'error') {
        throw new Error(event.message)
      }
    }
  }

  const handleAttachmentPick = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files ? Array.from(e.target.files) : []
    e.target.value = ''
    if (files.length === 0) return

    setAttachmentUploadError(null)
    setAttachmentUploading(true)
    setActivePanel(null)
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
        const result = await uploadMediaImage(imageFile)
        setPendingImages(prev => [...prev, { id: result.attachment_id, filename: imageFile.name }])
      }

      const knowledgeFile = knowledgeFiles[0]
      if (knowledgeFile) {
        await uploadKnowledgeFile(knowledgeFile)
      }
    } catch (err) {
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
    (input.trim().length > 0 || pendingImages.length > 0) && !isStreaming && !attachmentUploading
  const hasVisibleAttachments = uploadedKnowledgeFiles.length > 0 || pendingImages.length > 0
  const plusMenuOpen = activePanel === 'plus'
  const manageUploadsOpen = activePanel === 'manage-uploads'
  const modelMenuOpen = activePanel === 'model'
  const reasoningMenuOpen = activePanel === 'reasoning'
  const isNarrow = layoutDecisions.layoutMode === 'narrow'
  const composerIndicators = useMemo(
    () => getComposerIndicators(planModeEnabled, onPlanModeChange),
    [onPlanModeChange, planModeEnabled],
  )
  const controlPillStyle = (isOpen: boolean) =>
    ({
      color: 'var(--text-muted)',
      background: isOpen ? 'rgba(17,24,39,0.08)' : 'transparent',
      boxShadow: isOpen ? '0 6px 14px rgba(15,23,42,0.08)' : 'none',
    }) satisfies CSSProperties
  const composerMenuStyle = {
    borderColor: 'var(--input-border)',
    background: 'var(--composer-menu-bg)',
    backdropFilter: 'blur(14px)',
    boxShadow: '0 10px 20px rgba(15,23,42,0.08)',
  } satisfies CSSProperties

  return (
    <div
      className="chat-shell flex h-full min-h-0 min-w-0 flex-1 flex-col"
      style={{ background: 'var(--bg-chat)' }}
    >
      <div className="relative min-h-0 flex-1">
        <div
          className="pointer-events-none absolute inset-x-0 top-0 z-10 h-10"
          style={{
            background:
              'linear-gradient(180deg, var(--bg-chat) 0%, color-mix(in srgb, var(--bg-chat) 0%, transparent) 100%)',
          }}
        />
        <div
          className={`ui-static flex h-full flex-col overflow-y-auto ${layoutDecisions.compactSpacing ? 'space-y-3 px-3 py-4' : 'space-y-4 px-5 py-6'}`}
        >
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
          <div className={`flex h-full flex-col items-center justify-center text-center ${layoutDecisions.compactSpacing ? 'gap-4 px-3' : 'gap-5 px-4'}`}>
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
            <div
              className={`mt-2 grid w-full max-w-md gap-2 ${layoutDecisions.singleColumnPrompts ? 'grid-cols-1' : 'grid-cols-2'}`}
            >
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
              layoutMode={layoutDecisions.layoutMode}
            />
          ))
        )}
        <div ref={bottomRef} />
      </div>
      </div>

      <div
        className={`flex-shrink-0 ${layoutDecisions.compactComposer ? 'px-2.5 pb-2.5 pt-2' : 'px-4 pb-4 pt-3'}`}
        style={{ background: 'var(--bg-chat)' }}
      >
        <div className={`mx-auto space-y-2 ${layoutDecisions.compactComposer ? 'max-w-none' : 'max-w-4xl'}`}>
          <div
            ref={composerRef}
            className={`relative border shadow-[0_20px_48px_rgba(15,23,42,0.08)] ${layoutDecisions.compactComposer ? 'rounded-[24px] px-2.5 py-2' : 'rounded-[28px] px-3 py-2.5'}`}
            style={{
              borderColor: 'var(--input-border)',
              background: 'var(--composer-surface)',
            }}
          >
            <div ref={panelBoundaryRef} className="relative">
            {plusMenuOpen && (
              <div
                className={`absolute bottom-14 left-0 z-30 rounded-2xl border p-1.5 shadow-[0_10px_20px_rgba(15,23,42,0.08)] ${isNarrow ? 'w-[min(92vw,20rem)]' : 'w-[332px]'}`}
                style={composerMenuStyle}
              >
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="flex w-full items-center justify-between rounded-xl px-2.5 py-2 text-left text-[13px] transition-colors hover:bg-slate-900/[0.04]"
                  style={{ color: 'var(--text-main)' }}
                >
                  <span className="inline-flex items-center gap-2.5">
                    <span className="inline-flex h-4 w-4 items-center justify-center">
                      <UploadIcon />
                    </span>
                    <span>
                      <span className="block font-medium leading-none">Upload Files</span>
                      <span className="block text-xs" style={{ color: 'var(--text-muted)' }}>
                        Add images or knowledge files
                      </span>
                    </span>
                  </span>
                  <ChevronRightIcon />
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setActivePanel('manage-uploads')
                  }}
                  className="mt-0.5 flex w-full items-center justify-between rounded-xl px-2.5 py-2 text-left text-[13px] transition-colors hover:bg-slate-900/[0.04]"
                  style={{ color: 'var(--text-main)' }}
                >
                  <span className="inline-flex items-center gap-2.5">
                    <span className="inline-flex h-4 w-4 items-center justify-center">
                      <ManageIcon />
                    </span>
                    <span>
                      <span className="block font-medium leading-none">Manage Uploads</span>
                      <span className="block text-xs" style={{ color: 'var(--text-muted)' }}>
                        Review files and inclusion modes
                      </span>
                    </span>
                  </span>
                  <ChevronRightIcon />
                </button>

                <div
                  className="mt-0.5 flex items-center justify-between rounded-xl px-2.5 py-2"
                  style={{ color: 'var(--text-main)' }}
                >
                  <span className="inline-flex items-center gap-2.5">
                    <span className="inline-flex h-4 w-4 items-center justify-center">
                      <PlanModeIcon />
                    </span>
                    <span>
                      <span className="block text-[13px] font-medium leading-none">Plan Mode</span>
                      <span className="block text-xs whitespace-nowrap" style={{ color: 'var(--text-muted)' }}>
                        Frontend feature flag for planning flows
                      </span>
                    </span>
                  </span>
                  <button
                    type="button"
                    role="switch"
                    aria-checked={planModeEnabled}
                    onClick={() => onPlanModeChange(!planModeEnabled)}
                    className="relative inline-flex h-5 w-[34px] items-center rounded-full transition-colors"
                    style={{
                      background: planModeEnabled ? '#3b82f6' : 'rgba(15,23,42,0.12)',
                      cursor: 'default',
                    }}
                  >
                    <span
                      className="inline-flex h-3.5 w-3.5 rounded-full bg-white transition-transform"
                      style={{
                        transform: planModeEnabled ? 'translateX(17px)' : 'translateX(3px)',
                      }}
                    />
                  </button>
                </div>
              </div>
            )}

            {modelMenuOpen && (
              <div
                className={`absolute bottom-14 z-30 min-w-[180px] rounded-2xl border p-1.5 ${isNarrow ? 'left-9 w-[min(56vw,12rem)]' : 'left-10'}`}
                style={composerMenuStyle}
                role="menu"
                aria-label="Model menu"
              >
                {models.map(model => {
                  const isSelected = model === selectedModel
                  return (
                    <button
                      key={model}
                      type="button"
                      role="menuitemradio"
                      aria-checked={isSelected}
                      onClick={() => {
                        onModelChange(model)
                        setActivePanel(null)
                      }}
                      className="flex w-full items-center justify-between rounded-xl px-3 py-2 text-left text-[13px] transition-colors hover:bg-slate-900/[0.04]"
                      style={{ color: 'var(--text-main)' }}
                    >
                      <span className="truncate font-medium">{model}</span>
                      <span
                        className="ml-3 inline-flex h-4 w-4 items-center justify-center"
                        style={{ color: isSelected ? 'var(--text-main)' : 'transparent' }}
                      >
                        <CheckIcon />
                      </span>
                    </button>
                  )
                })}
              </div>
            )}

            {reasoningMenuOpen && (
              <div
                className={`absolute bottom-14 z-30 min-w-[148px] rounded-2xl border p-1.5 ${isNarrow ? 'left-[7.25rem] w-[min(44vw,10rem)]' : 'left-[152px]'}`}
                style={composerMenuStyle}
                role="menu"
                aria-label="Reasoning menu"
              >
                {(['low', 'medium', 'high'] as const).map(level => {
                  const isSelected = level === reasoningLevel
                  return (
                    <button
                      key={level}
                      type="button"
                      role="menuitemradio"
                      aria-checked={isSelected}
                      onClick={() => {
                        onReasoningLevelChange(level)
                        setActivePanel(null)
                      }}
                      className="flex w-full items-center justify-between rounded-xl px-3 py-2 text-left text-[13px] transition-colors hover:bg-slate-900/[0.04]"
                      style={{ color: 'var(--text-main)' }}
                    >
                      <span className="font-medium">{reasoningLabel(level)}</span>
                      <span
                        className="ml-3 inline-flex h-4 w-4 items-center justify-center"
                        style={{ color: isSelected ? 'var(--text-main)' : 'transparent' }}
                      >
                        <CheckIcon />
                      </span>
                    </button>
                  )
                })}
              </div>
            )}

            {manageUploadsOpen && (
              <div
                className="absolute bottom-14 left-0 z-30 w-[min(560px,calc(100vw-3rem))] rounded-3xl border p-4 shadow-[0_12px_24px_rgba(15,23,42,0.08)]"
                style={{
                  borderColor: 'var(--input-border)',
                  background: 'var(--composer-menu-bg-strong)',
                  backdropFilter: 'blur(18px)',
                }}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h3 className="text-sm font-semibold" style={{ color: 'var(--text-main)' }}>
                      Manage Uploads
                    </h3>
                    <p className="mt-1 text-xs" style={{ color: 'var(--text-muted)' }}>
                      Control which uploaded knowledge files flow into future turns.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setActivePanel(null)}
                    className="flex h-8 w-8 items-center justify-center rounded-full transition-colors hover:bg-slate-900/[0.04]"
                    style={{ color: 'var(--text-muted)' }}
                    title="Close upload manager"
                  >
                    <CloseIcon />
                  </button>
                </div>

                <div className="mt-4 max-h-[320px] space-y-3 overflow-y-auto pr-1">
                  {uploadedKnowledgeFiles.length === 0 && pendingImages.length === 0 ? (
                    <div
                      className="rounded-2xl border px-4 py-6 text-center text-sm"
                      style={{
                        borderColor: 'var(--input-border)',
                        background: 'var(--composer-muted-surface)',
                        color: 'var(--text-muted)',
                      }}
                    >
                      No uploaded files yet.
                    </div>
                  ) : (
                    <>
                      {uploadedKnowledgeFiles.map(file => (
                        <div
                          key={file.id}
                          className="rounded-2xl border px-4 py-3"
                          style={{
                            borderColor: 'var(--input-border)',
                            background: 'var(--composer-menu-bg)',
                          }}
                        >
                          <div className="flex items-start justify-between gap-3">
                            <div className="min-w-0">
                              <div
                                className="inline-flex items-center gap-2 text-sm font-medium"
                                style={{ color: 'var(--text-main)' }}
                              >
                                <DocumentIcon />
                                <span className="truncate">{file.filename}</span>
                              </div>
                              <div
                                className="mt-1 inline-flex items-center gap-2 text-xs"
                                style={{ color: 'var(--text-muted)' }}
                              >
                                {file.status === 'ready' ? <ReadyDot /> : <ProcessingDot />}
                                <span>
                                  {file.status === 'ready'
                                    ? `Mode: ${modeLabel(file.bindingMode)}`
                                    : 'Processing upload'}
                                </span>
                              </div>
                            </div>
                            <button
                              type="button"
                              onClick={() => onRemoveFileContext(file.id)}
                              className="rounded-full px-2.5 py-1 text-xs transition-colors hover:bg-slate-900/[0.04]"
                              style={{ color: 'var(--composer-danger-text)' }}
                            >
                              Delete
                            </button>
                          </div>

                          <div
                            className="mt-3 inline-flex overflow-hidden rounded-full border"
                            style={{
                              borderColor: 'var(--input-border)',
                              background: 'var(--composer-muted-surface)',
                            }}
                          >
                            {([
                              ['single', 'Next Turn'],
                              ['persistent', 'Sticky'],
                              ['idle', 'Inactive'],
                            ] as Array<[FileBindingMode, string]>).map(([mode, label]) => (
                              <button
                                key={mode}
                                type="button"
                                disabled={file.status !== 'ready'}
                                onClick={() => onSetFileContextMode(file.id, mode)}
                                className="border-l px-3 py-1.5 text-[11px] font-medium transition-colors first:border-l-0 disabled:cursor-not-allowed disabled:opacity-50"
                                style={{
                                  borderColor: 'rgba(15,23,42,0.08)',
                                  background:
                                    file.bindingMode === mode
                                      ? 'var(--composer-selected-surface)'
                                      : 'transparent',
                                  color:
                                    file.bindingMode === mode
                                      ? 'var(--text-main)'
                                      : 'var(--text-muted)',
                                }}
                              >
                                {label}
                              </button>
                            ))}
                          </div>
                        </div>
                      ))}
                      {pendingImages.length > 0 && (
                        <div className="space-y-3">
                          <p
                            className="px-1 text-[11px] font-medium uppercase tracking-[0.08em]"
                            style={{ color: 'var(--text-muted)' }}
                          >
                            Current Turn Images
                          </p>
                          {pendingImages.map(image => (
                            <div
                              key={image.id}
                              className="rounded-2xl border px-4 py-3"
                              style={{
                                borderColor: 'var(--input-border)',
                                background: 'var(--composer-menu-bg)',
                              }}
                            >
                              <div className="flex items-start justify-between gap-3">
                                <div className="min-w-0">
                                  <div
                                    className="inline-flex items-center gap-2 text-sm font-medium"
                                    style={{ color: 'var(--text-main)' }}
                                  >
                                    <ImageIcon />
                                    <span className="truncate">{image.filename}</span>
                                  </div>
                                  <p className="mt-1 text-xs" style={{ color: 'var(--text-muted)' }}>
                                    Vision attachments stay on the next send only.
                                  </p>
                                </div>
                                <button
                                  type="button"
                                  onClick={() =>
                                    setPendingImages(prev => prev.filter(item => item.id !== image.id))
                                  }
                                  className="rounded-full px-2.5 py-1 text-xs transition-colors hover:bg-slate-900/[0.04]"
                                  style={{ color: 'var(--composer-danger-text)' }}
                                >
                                  Delete
                                </button>
                              </div>
                              <div
                                className="mt-3 inline-flex overflow-hidden rounded-full border"
                                style={{
                                  borderColor: 'var(--input-border)',
                                  background: 'var(--composer-muted-surface)',
                                }}
                              >
                                <button
                                  type="button"
                                  className="px-3 py-1.5 text-[11px] font-medium"
                                  style={{
                                    background: 'var(--composer-selected-surface)',
                                    color: 'var(--text-main)',
                                  }}
                                >
                                  Next Turn
                                </button>
                                <button
                                  type="button"
                                  disabled
                                  className="border-l px-3 py-1.5 text-[11px] font-medium opacity-50"
                                  style={{
                                    borderColor: 'rgba(15,23,42,0.08)',
                                    color: 'var(--text-muted)',
                                  }}
                                  title="Sticky mode is not available for image attachments yet"
                                >
                                  Sticky
                                </button>
                                <button
                                  type="button"
                                  onClick={() =>
                                    setPendingImages(prev => prev.filter(item => item.id !== image.id))
                                  }
                                  className="border-l px-3 py-1.5 text-[11px] font-medium transition-colors"
                                  style={{
                                    borderColor: 'rgba(15,23,42,0.08)',
                                    color: 'var(--text-muted)',
                                  }}
                                >
                                  Inactive
                                </button>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </>
                  )}
                </div>
              </div>
            )}
            <div className="flex flex-col gap-2">
              <input
                ref={fileInputRef}
                type="file"
                accept={attachmentAccept}
                multiple
                className="hidden"
                onChange={handleAttachmentPick}
              />

              {hasVisibleAttachments && (
                <div
                  className="ui-static flex flex-wrap items-center gap-2 px-1 pt-1"
                  style={{ userSelect: 'none' }}
                >
                  {uploadedKnowledgeFiles.map(file => (
                    <div
                      key={file.id}
                      className="inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium"
                      style={{
                        borderColor: 'var(--composer-chip-border)',
                        background: 'transparent',
                        color: file.status === 'ready' ? 'var(--text-main)' : 'var(--text-muted)',
                      }}
                    >
                      {file.status === 'ready' ? <DocumentIcon /> : <ProcessingDot />}
                      <span className="max-w-[180px] truncate">{file.filename}</span>
                    </div>
                  ))}
                  {pendingImages.map(image => (
                    <div
                      key={image.id}
                      className="inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium"
                      style={{
                        borderColor: 'var(--composer-chip-border)',
                        background: 'transparent',
                        color: 'var(--text-main)',
                      }}
                    >
                      <ImageIcon />
                      <span className="max-w-[180px] truncate">{image.filename}</span>
                    </div>
                  ))}
                </div>
              )}

              <div
                data-testid="composer-text-surface"
                className="ui-static min-w-0 px-1 py-0.5"
                style={{ userSelect: 'none', caretColor: 'transparent' }}
                onMouseDown={event =>
                  handleComposerTextAreaPointerDown(event, textareaRef.current, () =>
                    setActivePanel(null),
                  )
                }
              >
                <textarea
                  ref={textareaRef}
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Message GOAT AI"
                  rows={1}
                  disabled={isStreaming}
                  className="w-full resize-none bg-transparent px-0 py-0 text-[15px] placeholder:text-zinc-400 focus:outline-none"
                  style={{
                    color: 'var(--text-main)',
                    fontWeight: 450,
                    letterSpacing: '-0.01em',
                    lineHeight: '22px',
                    minHeight: `${TEXTAREA_MIN_HEIGHT_PX}px`,
                    maxHeight: `${TEXTAREA_MAX_HEIGHT_PX}px`,
                    caretColor: 'var(--text-main)',
                    userSelect: 'text',
                  }}
                />
              </div>

              <div
                data-testid="composer-control-row"
                className="ui-static flex items-center justify-between gap-2 px-0.5"
              >
                <div
                  data-testid="composer-left-controls"
                  className={`-ml-1 flex min-w-0 flex-1 items-center ${layoutDecisions.compactComposer ? 'gap-1.5 overflow-x-auto pr-2' : 'gap-1.5'}`}
                  style={{
                    scrollbarWidth: 'none',
                    msOverflowStyle: 'none',
                  }}
                >
                  <button
                    type="button"
                    disabled={isStreaming || attachmentUploading}
                    onClick={() => {
                      setActivePanel(prev => (prev === 'plus' ? null : 'plus'))
                    }}
                    className={`${layoutDecisions.compactComposer ? 'h-9 w-9' : 'h-10 w-10'} flex flex-shrink-0 items-center justify-center rounded-full transition-all disabled:opacity-40`}
                    style={{ border: 'none', ...controlPillStyle(plusMenuOpen), color: 'rgba(17,24,39,0.42)' }}
                    title={plusMenuOpen ? 'Close actions' : 'Open upload and planning actions'}
                    onMouseEnter={e => {
                      if (!plusMenuOpen) e.currentTarget.style.background = 'rgba(17,24,39,0.08)'
                    }}
                    onMouseLeave={e => {
                      if (!plusMenuOpen) e.currentTarget.style.background = 'transparent'
                    }}
                  >
                    <PlusIcon />
                  </button>

                  <div className={`flex min-w-0 flex-shrink-0 items-center ${layoutDecisions.compactComposer ? 'gap-1.5' : 'gap-3'}`}>
                    <button
                      type="button"
                      aria-label="Open model menu"
                      aria-expanded={modelMenuOpen}
                      onClick={() => setActivePanel(prev => (prev === 'model' ? null : 'model'))}
                      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1.5 text-[13px] font-medium transition-all ${layoutDecisions.compactComposer ? 'max-w-[104px]' : 'max-w-[180px]'}`}
                      style={controlPillStyle(modelMenuOpen)}
                    >
                      <span className="truncate">{selectedModel}</span>
                      <span className="inline-flex flex-shrink-0 items-center justify-center">
                        <ChevronDownIcon />
                      </span>
                    </button>

                    <button
                      type="button"
                      aria-label="Open reasoning menu"
                      aria-expanded={reasoningMenuOpen}
                      onClick={() =>
                        setActivePanel(prev => (prev === 'reasoning' ? null : 'reasoning'))
                      }
                      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1.5 text-[13px] font-medium transition-all ${layoutDecisions.compactComposer ? 'max-w-[78px] flex-shrink-0' : ''}`}
                      style={controlPillStyle(reasoningMenuOpen)}
                    >
                      <span className="truncate">{reasoningLabel(reasoningLevel)}</span>
                      <span className="inline-flex flex-shrink-0 items-center justify-center">
                        <ChevronDownIcon />
                      </span>
                    </button>

                    {composerIndicators.length > 0 && (
                      <div className={`flex min-w-0 flex-shrink-0 items-center gap-2 ${layoutDecisions.compactComposer ? '' : 'ml-1'}`}>
                        {composerIndicators.map(indicator => {
                          const showTooltip = hoveredIndicator === indicator.key
                          return (
                            <button
                              key={indicator.key}
                              type="button"
                              className="relative inline-flex items-center gap-1.5 text-[13px] font-medium"
                              style={{ color: '#3b82f6' }}
                              aria-label={`${indicator.label} enabled`}
                              title={indicator.tooltip}
                              onClick={() => indicator.onClick?.()}
                              onMouseEnter={() => setHoveredIndicator(indicator.key)}
                              onMouseLeave={() => setHoveredIndicator(null)}
                              onFocus={() => setHoveredIndicator(indicator.key)}
                              onBlur={() => setHoveredIndicator(null)}
                            >
                              <span className="inline-flex h-4 w-4 items-center justify-center">
                                {indicator.icon}
                              </span>
                              <span>{indicator.label}</span>
                              {showTooltip && (
                                <span
                                  role="tooltip"
                                  className="pointer-events-none absolute bottom-[calc(100%+0.45rem)] left-1/2 z-20 -translate-x-1/2 whitespace-nowrap rounded-full px-2 py-1 text-[11px] font-medium shadow-[0_10px_20px_rgba(15,23,42,0.14)]"
                                  style={{
                                    background: 'var(--composer-menu-bg-strong)',
                                    color: 'var(--text-main)',
                                    border: '1px solid var(--input-border)',
                                  }}
                                >
                                  {indicator.tooltip}
                                </span>
                              )}
                            </button>
                          )
                        })}
                      </div>
                    )}
                  </div>
                </div>

                <div
                  data-testid="composer-right-controls"
                  className="flex flex-shrink-0 items-center gap-2"
                >
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
                    className="flex h-10 w-10 items-center justify-center rounded-full transition-all"
                    style={{
                      background: isStreaming ? '#111111' : canSend ? '#111111' : '#9ca3af',
                      color: '#ffffff',
                      boxShadow:
                        canSend || isStreaming ? 'none' : 'inset 0 0 0 1px rgba(0,0,0,0.04)',
                      cursor: 'default',
                    }}
                    title={isStreaming ? 'Stop generating' : 'Send message'}
                  >
                    {isStreaming ? <StopIcon /> : <SendArrowIcon />}
                  </button>
                </div>
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
                borderColor: 'var(--composer-danger-border)',
                background: 'var(--composer-danger-bg)',
                color: 'var(--composer-danger-fg)',
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
