import { useChat } from './hooks/useChat'
import { useModels } from './hooks/useModels'
import { useTheme } from './hooks/useTheme'
import { useUserName } from './hooks/useUserName'
import ChatWindow from './components/ChatWindow'
import Sidebar from './components/Sidebar'
import { ErrorBoundary } from './components/ErrorBoundary'

/** Root application — orchestrates hooks and wires state down to leaf components. */
export default function App() {
  const { theme, toggleTheme } = useTheme()
  const models = useModels()
  const chat = useChat()
  const { userName, setUserName } = useUserName()

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
      />
      <ErrorBoundary>
        <ChatWindow
          messages={chat.messages}
          isStreaming={chat.isStreaming}
          selectedModel={models.selectedModel}
          onSendMessage={content => void chat.sendMessage(content, models.selectedModel, userName)}
          onStop={chat.stopStreaming}
        />
      </ErrorBoundary>
    </div>
  )
}
