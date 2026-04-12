import { Suspense, lazy, useId, useMemo, useRef, type FC, type MouseEvent as ReactMouseEvent } from 'react'
import type { UploadStreamEvent } from '../api/upload'
import type { GPUStatus, InferenceLatency } from '../api/system'
import type { CodeSandboxFeature } from '../api/types'
import type { FileBindingMode, FileContextItem } from '../hooks/useFileContext'
import { useChatComposerState } from '../hooks/useChatComposerState'
import { useCodeSandboxController } from '../hooks/useCodeSandboxController'
import { useComposerAttachments } from '../hooks/useComposerAttachments'
import { useComposerPanels } from '../hooks/useComposerPanels'
import type { ChatLayoutDecisions } from '../utils/chatLayout'
import { brandingConfig } from '../config/branding'
import type { ReasoningLevel } from './chatComposerPrimitives'
import ComposerAttachmentStrip from './ComposerAttachmentStrip'
import ComposerControls from './ComposerControls'
import PlusMenu from './PlusMenu'
import ModelMenu from './ModelMenu'
import ReasoningMenu from './ReasoningMenu'

const LazyCodeSandboxPanel = lazy(() => import('./CodeSandboxPanel'))
const LazyManageUploadsPanel = lazy(() => import('./ManageUploadsPanel'))

export interface ChatComposerProps {
  isStreaming: boolean
  layoutDecisions: ChatLayoutDecisions
  models: string[]
  selectedModel: string
  onModelChange: (model: string) => void
  supportsVision?: boolean
  supportsThinking?: boolean
  fileContexts: FileContextItem[]
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
  event: ReactMouseEvent<HTMLDivElement>,
  textarea: HTMLTextAreaElement | null,
  closePanel: () => void,
): void {
  closePanel()
  if (event.target !== textarea && textarea) {
    event.preventDefault()
    textarea.focus()
  }
}

const ChatComposer: FC<ChatComposerProps> = ({
  isStreaming,
  layoutDecisions,
  models,
  selectedModel,
  onModelChange,
  supportsVision = false,
  supportsThinking = false,
  fileContexts,
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
  const fileInputRef = useRef<HTMLInputElement>(null)
  const panelBoundaryRef = useRef<HTMLDivElement>(null)
  const plusButtonRef = useRef<HTMLButtonElement | null>(null)
  const modelButtonRef = useRef<HTMLButtonElement | null>(null)
  const reasoningButtonRef = useRef<HTMLButtonElement | null>(null)
  const plusPanelId = useId()
  const modelMenuId = useId()
  const modelTriggerId = useId()
  const reasoningMenuId = useId()
  const reasoningTriggerId = useId()
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
  const {
    plusMenuOpen,
    manageUploadsOpen,
    modelMenuOpen,
    reasoningMenuOpen,
    codeSandboxOpen,
    modelMenuFocusStrategy,
    reasoningMenuFocusStrategy,
    setActivePanel,
    closeActivePanel,
    toggleComposerPanel,
    toggleModelMenu,
    toggleReasoningMenu,
    handleModelMenuTriggerKeyDown,
    handleReasoningMenuTriggerKeyDown,
  } = useComposerPanels({
    panelBoundaryRef,
    plusButtonRef,
    stopCodeSandboxMonitoring,
  })
  const uploadedKnowledgeFiles = useMemo(
    () => fileContexts.filter(item => item.documentId || item.status === 'processing'),
    [fileContexts],
  )
  const {
    input,
    textareaRef,
    canSend,
    setInput,
    handleSubmit,
    handleComposerKeyDown,
  } = useChatComposerState({
    isStreaming,
    attachmentUploading,
    pendingImageIds: pendingImages.map(item => item.id),
    onSendMessage,
    clearPendingImages,
    closeActivePanel,
  })
  const isNarrow = layoutDecisions.layoutMode === 'narrow'

  return (
    <div
      className={`flex-shrink-0 ${layoutDecisions.compactComposer ? 'px-2.5 pb-2.5 pt-2' : 'px-4 pb-4 pt-3'}`}
      style={{ background: 'var(--bg-chat)' }}
    >
      <div className={`mx-auto space-y-2 ${layoutDecisions.compactComposer ? 'max-w-none' : 'max-w-4xl'}`}>
        <div
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
              panelId={plusPanelId}
              triggerRef={plusButtonRef}
              codeSandboxFeature={codeSandboxFeature}
              planModeEnabled={planModeEnabled}
              supportsThinking={supportsThinking}
              thinkingEnabled={thinkingEnabled}
              onClose={closeActivePanel}
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
              onClose={closeActivePanel}
              onSelectModel={onModelChange}
            />
            <ReasoningMenu
              isOpen={reasoningMenuOpen}
              isNarrow={isNarrow}
              menuId={reasoningMenuId}
              triggerRef={reasoningButtonRef}
              focusStrategy={reasoningMenuFocusStrategy}
              reasoningLevel={reasoningLevel}
              onClose={closeActivePanel}
              onSelectReasoningLevel={onReasoningLevelChange}
            />
            {manageUploadsOpen && (
              <Suspense fallback={null}>
                <LazyManageUploadsPanel
                  isOpen={manageUploadsOpen}
                  uploadedKnowledgeFiles={uploadedKnowledgeFiles}
                  pendingImages={pendingImages}
                  onClose={closeActivePanel}
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
                  onClose={closeActivePanel}
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

              <ComposerAttachmentStrip
                uploadedKnowledgeFiles={uploadedKnowledgeFiles}
                pendingImages={pendingImages}
              />

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
                  onChange={event => setInput(event.target.value)}
                  onKeyDown={handleComposerKeyDown}
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
                    minHeight: '28px',
                    maxHeight: '144px',
                    caretColor: 'var(--text-main)',
                    userSelect: 'text',
                  }}
                />
              </div>
              <ComposerControls
                layoutDecisions={layoutDecisions}
                selectedModel={selectedModel}
                reasoningLevel={reasoningLevel}
                supportsThinking={supportsThinking}
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
                plusPanelId={plusMenuOpen ? plusPanelId : undefined}
                modelButtonRef={modelButtonRef}
                reasoningButtonRef={reasoningButtonRef}
                modelButtonId={modelTriggerId}
                reasoningButtonId={reasoningTriggerId}
                modelMenuId={modelMenuOpen ? modelMenuId : undefined}
                reasoningMenuId={reasoningMenuOpen ? reasoningMenuId : undefined}
                onTogglePlusMenu={() => {
                  toggleComposerPanel('plus')
                }}
                onToggleModelMenu={toggleModelMenu}
                onToggleReasoningMenu={toggleReasoningMenu}
                onModelMenuTriggerKeyDown={handleModelMenuTriggerKeyDown}
                onReasoningMenuTriggerKeyDown={handleReasoningMenuTriggerKeyDown}
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
  )
}

export default ChatComposer
