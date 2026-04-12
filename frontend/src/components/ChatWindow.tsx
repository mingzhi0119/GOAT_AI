import {
  Suspense,
  lazy,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type FC,
  type KeyboardEvent,
} from 'react'
import type { UploadStreamEvent } from '../api/upload'
import type { GPUStatus, InferenceLatency } from '../api/system'
import type {
  ChartSpec,
  CodeSandboxFeature,
  Message,
} from '../api/types'
import type { FileBindingMode, FileContextItem } from '../hooks/useFileContext'
import { useCodeSandboxController } from '../hooks/useCodeSandboxController'
import { useComposerAttachments } from '../hooks/useComposerAttachments'
import ComposerControls from './ComposerControls'
import EmptyChatState, { type EmptyChatPrompt } from './EmptyChatState'
import ModelMenu from './ModelMenu'
import PlusMenu from './PlusMenu'
import ReasoningMenu from './ReasoningMenu'
import { getSuffixPrompt, getTemplateFallbackPrompt } from '../utils/uploadPrompts'
import { pickRandomPromptTexts, STARTER_PROMPT_POOL } from '../utils/starterPrompts'
import type { ChatLayoutDecisions } from '../utils/chatLayout'
import MessageBubble from './MessageBubble'
import type { ReasoningLevel } from './chatComposerPrimitives'
import {
  DocumentIcon,
  ImageIcon,
  ProcessingDot,
  ReadyDot,
} from './chatComposerPrimitives'
import { brandingConfig } from '../config/branding'

const LazyChartCard = lazy(() => import('./ChartCard'))
const LazyCodeSandboxPanel = lazy(() => import('./CodeSandboxPanel'))
const LazyManageUploadsPanel = lazy(() => import('./ManageUploadsPanel'))
const LazyMessageBubble = lazy(() => import('./MessageBubble'))

const TEXTAREA_MAX_HEIGHT_PX = 144
const TEXTAREA_MIN_HEIGHT_PX = 28

type ComposerPanel = 'plus' | 'manage-uploads' | 'model' | 'reasoning' | 'code-sandbox' | null
type MenuFocusStrategy = 'selected' | 'first' | 'last'

interface Props {
  messages: Message[]
  chartSpec: ChartSpec | null
  isStreaming: boolean
  layoutDecisions: ChatLayoutDecisions
  models: string[]
  selectedModel: string
  onModelChange: (model: string) => void
  supportsVision?: boolean
  supportsThinking?: boolean
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
  codeSandboxFeature: CodeSandboxFeature | null
  planModeEnabled: boolean
  onPlanModeChange: (enabled: boolean) => void
  reasoningLevel: ReasoningLevel
  onReasoningLevelChange: (level: ReasoningLevel) => void
  thinkingEnabled: boolean
  onThinkingEnabledChange: (enabled: boolean) => void
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
  supportsThinking = false,
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
  codeSandboxFeature,
  planModeEnabled,
  onPlanModeChange,
  reasoningLevel,
  onReasoningLevelChange,
  thinkingEnabled,
  onThinkingEnabledChange,
}) => {
  const [input, setInput] = useState('')
  const [activePanel, setActivePanel] = useState<ComposerPanel>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const composerRef = useRef<HTMLDivElement>(null)
  const panelBoundaryRef = useRef<HTMLDivElement>(null)
  const plusButtonRef = useRef<HTMLButtonElement | null>(null)
  const modelButtonRef = useRef<HTMLButtonElement | null>(null)
  const reasoningButtonRef = useRef<HTMLButtonElement | null>(null)
  const previousCodeSandboxOpenRef = useRef(false)
  const previousCodeSandboxPanelRef = useRef(false)
  const modelMenuId = useId()
  const modelTriggerId = useId()
  const reasoningMenuId = useId()
  const reasoningTriggerId = useId()
  const [modelMenuFocusStrategy, setModelMenuFocusStrategy] =
    useState<MenuFocusStrategy>('selected')
  const [reasoningMenuFocusStrategy, setReasoningMenuFocusStrategy] =
    useState<MenuFocusStrategy>('selected')
  const hasActiveFileContext = activeFileContext !== null
  const activeFileContextFilename = activeFileContext?.filename ?? null
  const activeFileContextSuffixPrompt = activeFileContext?.suffixPrompt ?? null
  const activeFileContextTemplatePrompt = activeFileContext?.templatePrompt ?? null
  const {
    attachmentAccept,
    attachmentUploadError,
    attachmentUploading,
    pendingImages,
    clearPendingImages,
    handleAttachmentPick,
    removePendingImage,
  } = useComposerAttachments({
    supportsVision,
    onUploadEvent,
  })
  const {
    codeSandboxEnabled,
    sandboxCode,
    sandboxCommand,
    sandboxError,
    sandboxExecutionMode,
    sandboxLiveLogs,
    sandboxPending,
    sandboxResult,
    sandboxStdin,
    sandboxStreamDisconnected,
    clearSandboxError,
    runCodeSandbox,
    setSandboxCode,
    setSandboxCommand,
    setSandboxExecutionMode,
    setSandboxStdin,
    stopCodeSandboxMonitoring,
  } = useCodeSandboxController(codeSandboxFeature)

  const starterPrompts = useMemo<EmptyChatPrompt[]>(() => {
    const basePrompts = pickRandomPromptTexts(
      STARTER_PROMPT_POOL,
      hasActiveFileContext ? 2 : 4,
    ).map((text): EmptyChatPrompt => ({ text, kind: 'base' }))
    if (!hasActiveFileContext || !activeFileContextFilename) {
      return basePrompts
    }
    const filename = activeFileContextFilename
    return [
      ...basePrompts,
      {
        text: activeFileContextSuffixPrompt ?? getSuffixPrompt(filename),
        kind: 'suffix',
      },
      {
        text:
          activeFileContextTemplatePrompt ?? getTemplateFallbackPrompt(filename),
        kind: 'template',
      },
    ]
  }, [
    hasActiveFileContext,
    activeFileContextFilename,
    activeFileContextSuffixPrompt,
    activeFileContextTemplatePrompt,
  ])

  const visibleMessages = useMemo(() => messages.filter(message => !message.hidden), [messages])
  const sessionHasFileContext = fileContexts.length > 0 || messages.some(message => message.hidden)
  const uploadedKnowledgeFiles = useMemo(
    () => fileContexts.filter(item => item.documentId || item.status === 'processing'),
    [fileContexts],
  )
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
    clearPendingImages()
    setActivePanel(null)
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
  const codeSandboxOpen = activePanel === 'code-sandbox'
  const isNarrow = layoutDecisions.layoutMode === 'narrow'

  const toggleComposerPanel = (panel: Exclude<ComposerPanel, null>) => {
    setActivePanel(prev => (prev === panel ? null : panel))
  }

  const handleMenuTriggerKeyDown = (
    event: KeyboardEvent<HTMLButtonElement>,
    panel: 'model' | 'reasoning',
    setFocusStrategy: (strategy: MenuFocusStrategy) => void,
  ) => {
    if (event.key !== 'ArrowDown' && event.key !== 'ArrowUp') return
    event.preventDefault()
    setFocusStrategy(event.key === 'ArrowUp' ? 'last' : 'first')
    setActivePanel(panel)
  }

  useEffect(() => {
    if (
      (!codeSandboxOpen && previousCodeSandboxOpenRef.current) ||
      (!manageUploadsOpen && previousCodeSandboxOpenRef.current)
    ) {
      plusButtonRef.current?.focus()
    }
    previousCodeSandboxOpenRef.current = codeSandboxOpen || manageUploadsOpen
  }, [codeSandboxOpen, manageUploadsOpen])

  useEffect(() => {
    if (!codeSandboxOpen && previousCodeSandboxPanelRef.current) {
      stopCodeSandboxMonitoring()
    }
    previousCodeSandboxPanelRef.current = codeSandboxOpen
  }, [codeSandboxOpen, stopCodeSandboxMonitoring])

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
          <EmptyChatState
            starterPrompts={starterPrompts}
            selectedModel={selectedModel}
            layoutDecisions={layoutDecisions}
            onSendMessage={text => onSendMessage(text, undefined)}
          />
        ) : (
          <Suspense
            fallback={
              <div
                className="rounded-2xl border px-4 py-3 text-sm"
                style={{
                  borderColor: 'var(--border-color)',
                  background: 'var(--bg-asst-bubble)',
                  color: 'var(--text-muted)',
                }}
              >
                Loading responses...
              </div>
            }
          >
            {visibleMessages.map(message => (
              <LazyMessageBubble
                key={message.id}
                message={message}
                hasFileContext={sessionHasFileContext}
                layoutMode={layoutDecisions.layoutMode}
              />
            ))}
          </Suspense>
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
              <PlusMenu
                isOpen={plusMenuOpen}
                isNarrow={isNarrow}
                codeSandboxFeature={codeSandboxFeature}
                planModeEnabled={planModeEnabled}
                supportsThinking={supportsThinking ?? false}
                thinkingEnabled={thinkingEnabled}
                onOpenCodeSandbox={() => {
                  if (!codeSandboxEnabled) return
                  clearSandboxError()
                  setActivePanel('code-sandbox')
                }}
                onUploadFiles={() => fileInputRef.current?.click()}
                onOpenManageUploads={() => setActivePanel('manage-uploads')}
                onTogglePlanMode={() => onPlanModeChange(!planModeEnabled)}
                onToggleThinkingMode={() => onThinkingEnabledChange(!thinkingEnabled)}
              />
              <ModelMenu
                isOpen={modelMenuOpen}
                isNarrow={isNarrow}
                menuId={modelMenuId}
                triggerRef={modelButtonRef}
                focusStrategy={modelMenuFocusStrategy}
                models={models}
                selectedModel={selectedModel}
                onClose={() => setActivePanel(null)}
                onSelectModel={model => {
                  onModelChange(model)
                  setActivePanel(null)
                }}
              />
              <ReasoningMenu
                isOpen={reasoningMenuOpen}
                isNarrow={isNarrow}
                menuId={reasoningMenuId}
                triggerRef={reasoningButtonRef}
                focusStrategy={reasoningMenuFocusStrategy}
                reasoningLevel={reasoningLevel}
                onClose={() => setActivePanel(null)}
                onSelectReasoningLevel={level => {
                  onReasoningLevelChange(level)
                  setActivePanel(null)
                }}
              />
              {manageUploadsOpen && (
                <Suspense fallback={null}>
                  <LazyManageUploadsPanel
                    isOpen={manageUploadsOpen}
                    uploadedKnowledgeFiles={uploadedKnowledgeFiles}
                    pendingImages={pendingImages}
                    onClose={() => setActivePanel(null)}
                    onRemoveFileContext={onRemoveFileContext}
                    onSetFileContextMode={onSetFileContextMode}
                    onRemovePendingImage={id => removePendingImage(id)}
                  />
                </Suspense>
              )}
              {codeSandboxOpen && (
                <Suspense fallback={null}>
                  <LazyCodeSandboxPanel
                    isOpen={codeSandboxOpen}
                    feature={codeSandboxFeature}
                    runtimeEnabled={codeSandboxEnabled}
                    runPending={sandboxPending}
                    executionMode={sandboxExecutionMode}
                    code={sandboxCode}
                    command={sandboxCommand}
                    stdin={sandboxStdin}
                    error={sandboxError}
                    result={sandboxResult}
                    liveLogs={sandboxLiveLogs}
                    streamDisconnected={sandboxStreamDisconnected}
                    onClose={() => setActivePanel(null)}
                    onExecutionModeChange={setSandboxExecutionMode}
                    onCodeChange={setSandboxCode}
                    onCommandChange={setSandboxCommand}
                    onStdinChange={setSandboxStdin}
                    onRun={() => {
                      void runCodeSandbox()
                    }}
                  />
                </Suspense>
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
                  aria-label={`Message ${brandingConfig.displayName}`}
                  placeholder={`Message ${brandingConfig.displayName}`}
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
              <ComposerControls
                layoutDecisions={layoutDecisions}
                selectedModel={selectedModel}
                reasoningLevel={reasoningLevel}
                supportsThinking={supportsThinking ?? false}
                thinkingEnabled={thinkingEnabled}
                planModeEnabled={planModeEnabled}
                onPlanModeChange={onPlanModeChange}
                plusMenuOpen={plusMenuOpen}
                modelMenuOpen={modelMenuOpen}
                reasoningMenuOpen={reasoningMenuOpen}
                isStreaming={isStreaming}
                attachmentUploading={attachmentUploading}
                canSend={canSend}
                gpuStatus={gpuStatus}
                gpuError={gpuError}
                inferenceLatency={inferenceLatency}
                plusButtonRef={plusButtonRef}
                modelButtonRef={modelButtonRef}
                reasoningButtonRef={reasoningButtonRef}
                modelButtonId={modelTriggerId}
                reasoningButtonId={reasoningTriggerId}
                modelMenuId={modelMenuOpen ? modelMenuId : undefined}
                reasoningMenuId={reasoningMenuOpen ? reasoningMenuId : undefined}
                onTogglePlusMenu={() => {
                  toggleComposerPanel('plus')
                }}
                onToggleModelMenu={() => {
                  setModelMenuFocusStrategy('selected')
                  toggleComposerPanel('model')
                }}
                onToggleReasoningMenu={() => {
                  setReasoningMenuFocusStrategy('selected')
                  toggleComposerPanel('reasoning')
                }}
                onModelMenuTriggerKeyDown={event => {
                  handleMenuTriggerKeyDown(event, 'model', setModelMenuFocusStrategy)
                }}
                onReasoningMenuTriggerKeyDown={event => {
                  handleMenuTriggerKeyDown(event, 'reasoning', setReasoningMenuFocusStrategy)
                }}
                onThinkingEnabledChange={onThinkingEnabledChange}
                thinkingTooltipEnabled={false}
                onStop={onStop}
                onSubmit={handleSubmit}
              />
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
