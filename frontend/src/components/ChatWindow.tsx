import { Suspense, lazy, useEffect, useMemo, useRef, type FC } from 'react'
import type { UploadStreamEvent } from '../api/upload'
import type { GPUStatus, InferenceLatency } from '../api/system'
import type { ChartSpec, CodeSandboxFeature, Message, RuntimeFeature } from '../api/types'
import type { FileBindingMode, FileContextItem } from '../hooks/useFileContext'
import ChatComposer from './ChatComposer'
import EmptyChatState, { type EmptyChatPrompt } from './EmptyChatState'
import { getSuffixPrompt, getTemplateFallbackPrompt } from '../utils/uploadPrompts'
import { pickRandomPromptTexts, STARTER_PROMPT_POOL } from '../utils/starterPrompts'
import type { ChatLayoutDecisions } from '../utils/chatLayout'
import type { ReasoningLevel } from './chatComposerPrimitives'

const LazyChartCard = lazy(() => import('./ChartCard'))
const LazyMessageBubble = lazy(() => import('./MessageBubble'))

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
  planModeAvailable?: boolean
  planModeAvailability?: string
  planModeFeature?: RuntimeFeature | null
  onPlanModeChange: (enabled: boolean) => void
  reasoningLevel: ReasoningLevel
  onReasoningLevelChange: (level: ReasoningLevel) => void
  thinkingEnabled: boolean
  onThinkingEnabledChange: (enabled: boolean) => void
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
  planModeAvailable = true,
  planModeAvailability,
  planModeFeature,
  onPlanModeChange,
  reasoningLevel,
  onReasoningLevelChange,
  thinkingEnabled,
  onThinkingEnabledChange,
}) => {
  const bottomRef = useRef<HTMLDivElement>(null)
  const starterPrompts = useMemo<EmptyChatPrompt[]>(() => {
    const basePrompts = pickRandomPromptTexts(
      STARTER_PROMPT_POOL,
      activeFileContext ? 2 : 4,
    ).map((text): EmptyChatPrompt => ({ text, kind: 'base' }))
    if (!activeFileContext?.filename) {
      return basePrompts
    }
    return [
      ...basePrompts,
      {
        text: activeFileContext.suffixPrompt ?? getSuffixPrompt(activeFileContext.filename),
        kind: 'suffix',
      },
      {
        text:
          activeFileContext.templatePrompt ??
          getTemplateFallbackPrompt(activeFileContext.filename),
        kind: 'template',
      },
    ]
  }, [activeFileContext])

  const visibleMessages = useMemo(() => messages.filter(message => !message.hidden), [messages])
  const sessionHasFileContext = fileContexts.length > 0 || messages.some(message => message.hidden)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

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
          <div ref={bottomRef} data-chat-bottom-anchor="true" />
        </div>
      </div>

      <ChatComposer
        isStreaming={isStreaming}
        layoutDecisions={layoutDecisions}
        models={models}
        selectedModel={selectedModel}
        onModelChange={onModelChange}
        supportsVision={supportsVision}
        supportsThinking={supportsThinking}
        fileContexts={fileContexts}
        onUploadEvent={onUploadEvent}
        onSendMessage={onSendMessage}
        onSetFileContextMode={onSetFileContextMode}
        onRemoveFileContext={onRemoveFileContext}
        onStop={onStop}
        gpuStatus={gpuStatus}
        gpuError={gpuError}
        inferenceLatency={inferenceLatency}
        codeSandboxFeature={codeSandboxFeature}
        planModeEnabled={planModeEnabled}
        planModeAvailable={planModeAvailable}
        planModeAvailability={planModeAvailability}
        planModeFeature={planModeFeature}
        onPlanModeChange={onPlanModeChange}
        reasoningLevel={reasoningLevel}
        onReasoningLevelChange={onReasoningLevelChange}
        thinkingEnabled={thinkingEnabled}
        onThinkingEnabledChange={onThinkingEnabledChange}
      />
    </div>
  )
}

export default ChatWindow
