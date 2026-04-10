import { useEffect, useMemo, useRef, useState } from 'react'
import { useAdvancedSettings } from './hooks/useAdvancedSettings'
import { useAppearance } from './hooks/useAppearance'
import { useChatLayoutMode } from './hooks/useChatLayoutMode'
import { useChatSession } from './hooks/useChatSession'
import { useGpuStatus } from './hooks/useGpuStatus'
import { useModels } from './hooks/useModels'
import { useSystemInstruction } from './hooks/useSystemInstruction'
import { useUserName } from './hooks/useUserName'
import { getChatLayoutDecisions } from './utils/chatLayout'
import { downloadChatAsMarkdown } from './utils/exportChatMarkdown'
import AppearancePanel from './components/AppearancePanel'
import ChatWindow from './components/ChatWindow'
import { ErrorBoundary } from './components/ErrorBoundary'
import Sidebar from './components/Sidebar'
import TopBar from './components/TopBar'
import type { UploadStreamEvent } from './api/upload'

/** Root application: compose stateful controllers and render the shell UI. */
export default function App() {
  const [planModeEnabled, setPlanModeEnabled] = useState(false)
  const [reasoningLevel, setReasoningLevel] = useState<'low' | 'medium' | 'high'>('medium')
  const [thinkingEnabled, setThinkingEnabled] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [appearanceOpen, setAppearanceOpen] = useState(false)
  const { appearance, effectiveMode, appearanceSummary, updateAppearance, resetAppearance } =
    useAppearance()
  const models = useModels()
  const { layoutMode } = useChatLayoutMode()
  const chatLayout = useMemo(() => getChatLayoutDecisions(layoutMode), [layoutMode])
  const supportsThinking = models.capabilities?.supports_thinking ?? false
  const effectiveThinkingEnabled = supportsThinking && thinkingEnabled
  const { userName, setUserName } = useUserName()
  const { systemInstruction, setSystemInstruction } = useSystemInstruction()
  const advanced = useAdvancedSettings()
  const session = useChatSession({
    selectedModel: models.selectedModel,
    userName,
    systemInstruction,
    ollamaOptions: advanced.getOptionsForRequest(effectiveThinkingEnabled),
  })
  const gpu = useGpuStatus(session.isStreaming)
  const { refreshNow } = gpu
  const wasStreamingRef = useRef(session.isStreaming)

  useEffect(() => {
    setSidebarOpen(chatLayout.sidebarBehavior === 'docked')
  }, [chatLayout.sidebarBehavior])

  useEffect(() => {
    const wasStreaming = wasStreamingRef.current
    wasStreamingRef.current = session.isStreaming
    if (!wasStreaming || session.isStreaming) return

    const timer = window.setTimeout(() => {
      void refreshNow()
    }, 1000)
    return () => window.clearTimeout(timer)
  }, [refreshNow, session.isStreaming])

  const handleDeleteAllHistory = () => {
    if (
      !window.confirm(
        'Delete all saved conversations from the server? This cannot be undone. Your current chat will also be cleared.',
      )
    ) {
      return
    }
    void session.deleteAllHistory().then(() => {
      session.clearChatSession()
    })
  }

  const handleUploadEvent = (event: UploadStreamEvent) => {
    if (event.type === 'file_prompt') {
      session.upsertFileContext({
        filename: event.filename,
        suffixPrompt: event.suffix_prompt,
        status: 'processing',
      })
      return
    }
    if (event.type === 'knowledge_ready') {
      session.upsertFileContext({
        filename: event.filename,
        documentId: event.document_id,
        ingestionId: event.ingestion_id,
        retrievalMode: event.retrieval_mode,
        suffixPrompt: event.suffix_prompt,
        templatePrompt: event.template_prompt,
        status: 'ready',
      })
    }
  }

  return (
    <div className="relative flex h-screen overflow-hidden" style={{ background: 'var(--bg-main)' }}>
      {chatLayout.sidebarBehavior === 'overlay' && sidebarOpen && (
        <button
          type="button"
          aria-label="Close sidebar overlay"
          className="absolute inset-0 z-30 bg-black/20 backdrop-blur-[1px]"
          onClick={() => setSidebarOpen(false)}
        />
      )}
      <Sidebar
        onClearChat={session.clearChatSession}
        userName={userName}
        onUserNameChange={setUserName}
        themeStyle={appearance.themeStyle}
        currentSessionId={session.sessionId}
        layoutMode={layoutMode}
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        historySessions={session.historySessions}
        isLoadingHistory={session.isLoadingHistory}
        historyError={session.historyError}
        onRefreshHistory={() => void session.refreshHistory()}
        onDeleteAllHistory={handleDeleteAllHistory}
        onLoadHistorySession={sessionId => {
          void session.loadHistorySession(sessionId)
        }}
        onDeleteHistorySession={sessionId => {
          void session.deleteHistorySession(sessionId)
        }}
      />
      <div className="flex flex-col flex-1 min-w-0 min-h-0">
        <TopBar
          sessionTitle={session.sessionTitle}
          modelCapabilities={models.capabilities?.capabilities ?? null}
          appearanceSummary={appearanceSummary}
          layoutMode={layoutMode}
          onSidebarToggle={() => setSidebarOpen(open => !open)}
          onOpenAppearance={() => setAppearanceOpen(true)}
          systemInstruction={systemInstruction}
          onSystemInstructionChange={setSystemInstruction}
          onExportMarkdown={() =>
            downloadChatAsMarkdown(
              session.messages.filter(message => !message.hidden),
              session.sessionTitle,
            )
          }
          advancedOpen={advanced.advancedOpen}
          onAdvancedOpenChange={advanced.setAdvancedOpen}
          temperature={advanced.temperature}
          onTemperatureChange={advanced.setTemperature}
          maxTokens={advanced.maxTokens}
          onMaxTokensChange={advanced.setMaxTokens}
          topP={advanced.topP}
          onTopPChange={advanced.setTopP}
          onResetAdvanced={advanced.resetAdvancedToDefaults}
        />
        <ErrorBoundary>
          <ChatWindow
            messages={session.messages}
            chartSpec={session.chartSpec}
            isStreaming={session.isStreaming}
            layoutDecisions={chatLayout}
            models={models.models}
            selectedModel={models.selectedModel}
            onModelChange={models.setSelectedModel}
            supportsVision={models.capabilities?.supports_vision ?? false}
            supportsThinking={supportsThinking}
            fileContexts={session.fileContexts}
            activeFileContext={session.activeFileContext}
            onUploadEvent={handleUploadEvent}
            onSendMessage={(content, imageIds) => {
              void session.sendMessage(content, imageIds)
            }}
            onSetFileContextMode={session.setFileContextBindingMode}
            onRemoveFileContext={session.removeFileContext}
            onStop={session.stopStreaming}
            gpuStatus={gpu.status}
            gpuError={gpu.error}
            inferenceLatency={gpu.inference}
            planModeEnabled={planModeEnabled}
            onPlanModeChange={setPlanModeEnabled}
            reasoningLevel={reasoningLevel}
            onReasoningLevelChange={setReasoningLevel}
            thinkingEnabled={effectiveThinkingEnabled}
            onThinkingEnabledChange={setThinkingEnabled}
          />
        </ErrorBoundary>
      </div>
      <AppearancePanel
        open={appearanceOpen}
        appearance={appearance}
        effectiveMode={effectiveMode}
        onClose={() => setAppearanceOpen(false)}
        onChange={updateAppearance}
        onReset={resetAppearance}
      />
    </div>
  )
}
