import { useChat } from './hooks/useChat'
import { useModels } from './hooks/useModels'
import { useTheme } from './hooks/useTheme'
import { useUserName } from './hooks/useUserName'
import { useHistory } from './hooks/useHistory'
import { useFileContext } from './hooks/useFileContext'
import { useGpuStatus } from './hooks/useGpuStatus'
import { useSystemInstruction } from './hooks/useSystemInstruction'
import { useAdvancedSettings } from './hooks/useAdvancedSettings'
import { downloadChatAsMarkdown } from './utils/exportChatMarkdown'
import type { ChartSpec } from './api/types'
import ChatWindow from './components/ChatWindow'
import Sidebar from './components/Sidebar'
import TopBar from './components/TopBar'
import { ErrorBoundary } from './components/ErrorBoundary'
import { useMemo, useState } from 'react'

/** Root application — orchestrates hooks and wires state down to leaf components. */
export default function App() {
  const { theme, toggleTheme } = useTheme()
  const models = useModels()
  const chat = useChat()
  const { userName, setUserName } = useUserName()
  const history = useHistory()
  const { fileContext, setFileContext, clearFileContext } = useFileContext()
  const { systemInstruction, setSystemInstruction } = useSystemInstruction()
  const advanced = useAdvancedSettings()
  const gpu = useGpuStatus(chat.isStreaming)
  const [chartSpec, setChartSpec] = useState<ChartSpec | null>(null)

  /** Title for top bar: server session title after save, else first visible user line (optimistic). */
  const sessionTitleForTopBar = useMemo(() => {
    const sid = chat.sessionId
    if (!sid) return null
    const fromList = history.sessions.find(s => s.id === sid)?.title?.trim()
    if (fromList) return fromList
    // Skip hidden messages (e.g. injected file-context prompts) when picking the title.
    const firstUser = chat.messages.find(
      m => m.role === 'user' && !m.isStreaming && !m.hidden && m.content.trim().length > 0,
    )
    if (firstUser) {
      const t = firstUser.content.trim().replace(/\n/g, ' ')
      return t.length > 80 ? `${t.slice(0, 80)}…` : t
    }
    return null
  }, [chat.sessionId, chat.messages, history.sessions])

  const handleClearChat = () => {
    chat.clearMessages()
    clearFileContext()
    setChartSpec(null)
  }

  const handleDeleteAllHistory = () => {
    if (
      !window.confirm(
        'Delete all saved conversations from the server? This cannot be undone. Your current chat will also be cleared.',
      )
    ) {
      return
    }
    void history.deleteAll().then(() => {
      chat.clearMessages()
    })
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar
        models={models.models}
        selectedModel={models.selectedModel}
        onModelChange={models.setSelectedModel}
        onRefreshModels={models.refresh}
        onClearChat={handleClearChat}
        isLoadingModels={models.isLoading}
        modelsError={models.error}
        userName={userName}
        onUserNameChange={setUserName}
        historySessions={history.sessions}
        isLoadingHistory={history.isLoading}
        historyError={history.error}
        onRefreshHistory={() => void history.refresh()}
        onDeleteAllHistory={handleDeleteAllHistory}
        onLoadHistorySession={sessionId => {
          void history.loadSession(sessionId).then(session => {
            // Restore the chart spec from the __chart__ sentinel stored in the session
            // (the backend appends it after every response that contained a chart block).
            const allMsgs = session.messages as Array<{ role: string; content: string }>
            const chartMessages = allMsgs.filter(m => m.role === '__chart__')
            const lastChart = chartMessages[chartMessages.length - 1]
            if (lastChart) {
              try {
                setChartSpec(JSON.parse(lastChart.content) as ChartSpec)
              } catch {
                setChartSpec(null)
              }
            } else {
              setChartSpec(null)
            }
            chat.loadSession(session.id, session.messages)
            // Clear the active file-upload context; the file context is already
            // embedded as hidden messages in the session so the LLM still has memory.
            clearFileContext()
          })
        }}
        onDeleteHistorySession={sessionId => {
          void history.deleteSession(sessionId)
        }}
        fileContext={fileContext}
        onFileContext={setFileContext}
        onChartSpec={setChartSpec}
        onClearFileContext={() => {
          clearFileContext()
          chat.clearMessages()
          setChartSpec(null)
        }}
      />
      <div className="flex flex-col flex-1 min-w-0 min-h-0">
        <TopBar
          sessionTitle={sessionTitleForTopBar}
          theme={theme}
          onToggleTheme={toggleTheme}
          systemInstruction={systemInstruction}
          onSystemInstructionChange={setSystemInstruction}
          onExportMarkdown={() =>
            downloadChatAsMarkdown(chat.messages.filter(m => !m.hidden), sessionTitleForTopBar)
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
            messages={chat.messages}
            chartSpec={chartSpec}
            isStreaming={chat.isStreaming}
            selectedModel={models.selectedModel}
            fileContext={fileContext}
            onSendMessage={content => {
              void chat
                .sendMessage(
                  content,
                  models.selectedModel,
                  userName,
                  fileContext?.prompt,
                  systemInstruction,
                  advanced.getOptionsForRequest(),
                  setChartSpec,
                )
                .then(() => history.refresh())
            }}
            onStop={chat.stopStreaming}
            gpuStatus={gpu.status}
            gpuError={gpu.error}
            inferenceLatency={gpu.inference}
          />
        </ErrorBoundary>
      </div>
    </div>
  )
}
