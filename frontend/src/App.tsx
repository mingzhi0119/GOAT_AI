import { useEffect, useRef } from 'react'
import { useAdvancedSettings } from './hooks/useAdvancedSettings'
import { useChatSession } from './hooks/useChatSession'
import { useGpuStatus } from './hooks/useGpuStatus'
import { useModels } from './hooks/useModels'
import { useSystemInstruction } from './hooks/useSystemInstruction'
import { useTheme } from './hooks/useTheme'
import { useUserName } from './hooks/useUserName'
import { downloadChatAsMarkdown } from './utils/exportChatMarkdown'
import ChatWindow from './components/ChatWindow'
import { ErrorBoundary } from './components/ErrorBoundary'
import Sidebar from './components/Sidebar'
import TopBar from './components/TopBar'
import type { UploadStreamEvent } from './api/upload'

/** Root application: compose stateful controllers and render the shell UI. */
export default function App() {
  const { theme, toggleTheme } = useTheme()
  const models = useModels()
  const { userName, setUserName } = useUserName()
  const { systemInstruction, setSystemInstruction } = useSystemInstruction()
  const advanced = useAdvancedSettings()
  const session = useChatSession({
    selectedModel: models.selectedModel,
    userName,
    systemInstruction,
    ollamaOptions: advanced.getOptionsForRequest(),
  })
  const gpu = useGpuStatus(session.isStreaming)
  const { refreshNow } = gpu
  const wasStreamingRef = useRef(session.isStreaming)

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
      session.setFileContext({
        filename: event.filename,
        suffixPrompt: event.suffix_prompt,
      })
      return
    }
    if (event.type === 'knowledge_ready') {
      session.setFileContext({
        filename: event.filename,
        documentId: event.document_id,
        ingestionId: event.ingestion_id,
        retrievalMode: event.retrieval_mode,
        suffixPrompt: event.suffix_prompt,
        templatePrompt: event.template_prompt,
      })
    }
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar
        models={models.models}
        selectedModel={models.selectedModel}
        onModelChange={models.setSelectedModel}
        onRefreshModels={models.refresh}
        onClearChat={session.clearChatSession}
        isLoadingModels={models.isLoading}
        isLoadingModelCapabilities={models.isLoadingCapabilities}
        modelsError={models.error}
        modelCapabilities={models.capabilities}
        modelCapabilitiesError={models.capabilitiesError}
        userName={userName}
        onUserNameChange={setUserName}
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
          theme={theme}
          onToggleTheme={toggleTheme}
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
            selectedModel={models.selectedModel}
            supportsVision={models.capabilities?.supports_vision ?? false}
            fileContext={session.fileContext}
            onUploadEvent={handleUploadEvent}
            onSendMessage={(content, imageIds) => {
              void session.sendMessage(content, imageIds)
            }}
            onSetFileContextMode={session.setFileContextBindingMode}
            onStop={session.stopStreaming}
            onClearFileContext={session.clearFileContextSession}
            gpuStatus={gpu.status}
            gpuError={gpu.error}
            inferenceLatency={gpu.inference}
          />
        </ErrorBoundary>
      </div>
    </div>
  )
}
