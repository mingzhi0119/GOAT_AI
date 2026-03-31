import { useChat } from './hooks/useChat'
import { useModels } from './hooks/useModels'
import { useTheme } from './hooks/useTheme'
import { useUserName } from './hooks/useUserName'
import { useHistory } from './hooks/useHistory'
import { useFileContext } from './hooks/useFileContext'
import { useGpuStatus } from './hooks/useGpuStatus'
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
  const gpu = useGpuStatus(chat.isStreaming)
  const [chartSpec, setChartSpec] = useState<ChartSpec | null>(null)

  /** Title for top bar: server session title after save, else first user line (optimistic). */
  const sessionTitleForTopBar = useMemo(() => {
    const sid = chat.sessionId
    if (!sid) return null
    const fromList = history.sessions.find(s => s.id === sid)?.title?.trim()
    if (fromList) return fromList
    const firstUser = chat.messages.find(
      m => m.role === 'user' && !m.isStreaming && m.content.trim().length > 0,
    )
    if (firstUser) {
      const t = firstUser.content.trim().replace(/\n/g, ' ')
      return t.length > 80 ? `${t.slice(0, 80)}…` : t
    }
    return null
  }, [chat.sessionId, chat.messages, history.sessions])

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
        onClearChat={chat.clearMessages}
        isLoadingModels={models.isLoading}
        modelsError={models.error}
        onStream={chat.streamToChat}
        userName={userName}
        onUserNameChange={setUserName}
        historySessions={history.sessions}
        isLoadingHistory={history.isLoading}
        historyError={history.error}
        onRefreshHistory={() => void history.refresh()}
        onDeleteAllHistory={handleDeleteAllHistory}
        onLoadHistorySession={sessionId => {
          void history.loadSession(sessionId).then(session => {
            chat.loadSession(session.id, session.messages)
          })
        }}
        onDeleteHistorySession={sessionId => {
          void history.deleteSession(sessionId)
        }}
        fileContext={fileContext}
        onFileContext={setFileContext}
        onChartSpec={setChartSpec}
        onClearFileContext={clearFileContext}
      />
      <div className="flex flex-col flex-1 min-w-0 min-h-0">
        <TopBar sessionTitle={sessionTitleForTopBar} theme={theme} onToggleTheme={toggleTheme} />
        <ErrorBoundary>
          <ChatWindow
            messages={chat.messages}
            chartSpec={chartSpec}
            isStreaming={chat.isStreaming}
            selectedModel={models.selectedModel}
            onSendMessage={content => {
              void chat
                .sendMessage(content, models.selectedModel, userName, fileContext?.prompt)
                .then(() => history.refresh())
            }}
            onStop={chat.stopStreaming}
            gpuStatus={gpu.status}
            gpuError={gpu.error}
          />
        </ErrorBoundary>
      </div>
    </div>
  )
}
