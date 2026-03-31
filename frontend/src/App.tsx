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
import { ErrorBoundary } from './components/ErrorBoundary'
import { useState } from 'react'

/** Root application — orchestrates hooks and wires state down to leaf components. */
export default function App() {
  const { theme, toggleTheme } = useTheme()
  const models = useModels()
  const chat = useChat()
  const { userName, setUserName } = useUserName()
  const history = useHistory()
  const { fileContext, setFileContext, clearFileContext } = useFileContext()
  const gpu = useGpuStatus()
  const [chartSpec, setChartSpec] = useState<ChartSpec | null>(null)

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
        theme={theme}
        onToggleTheme={toggleTheme}
        userName={userName}
        onUserNameChange={setUserName}
        historySessions={history.sessions}
        isLoadingHistory={history.isLoading}
        historyError={history.error}
        onRefreshHistory={() => void history.refresh()}
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
        gpuStatus={gpu.status}
        gpuError={gpu.error}
      />
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
        />
      </ErrorBoundary>
    </div>
  )
}
