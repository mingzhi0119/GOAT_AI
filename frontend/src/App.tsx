import { Suspense, lazy, useEffect, useMemo, useState } from 'react'
import type { RuntimeFeature } from './api/types'
import ChatWindow from './components/ChatWindow'
import { ErrorBoundary } from './components/ErrorBoundary'
import Sidebar from './components/Sidebar'
import TopBar from './components/TopBar'
import { useBranding } from './config/branding'
import { useAdvancedSettings } from './hooks/useAdvancedSettings'
import { useAppearance } from './hooks/useAppearance'
import { useChatLayoutMode } from './hooks/useChatLayoutMode'
import { useChatSession } from './hooks/useChatSession'
import { useChatShellActions } from './hooks/useChatShellActions'
import { useDesktopDiagnostics } from './hooks/useDesktopDiagnostics'
import { useGpuStatus } from './hooks/useGpuStatus'
import { useModels } from './hooks/useModels'
import { useSystemFeatures } from './hooks/useSystemFeatures'
import { useSystemInstruction } from './hooks/useSystemInstruction'
import { useUserName } from './hooks/useUserName'
import { reportDesktopBootstrapStatus } from './utils/desktopBootstrap'
import { downloadChatAsMarkdown } from './utils/exportChatMarkdown'
import { getChatLayoutDecisions } from './utils/chatLayout'

const LazyAppearancePanel = lazy(() => import('./components/AppearancePanel'))

interface AppShellProps {
  appTitle: string
}

function describePlanModeAvailability(feature: RuntimeFeature | null): string {
  if (!feature) return 'Checking backend planning readiness'
  if (feature.effective_enabled) return 'Backend planning runtime is ready for this caller'
  if (feature.deny_reason === 'permission_denied') return 'Not available for this API key'
  if (feature.deny_reason === 'disabled_by_operator') {
    return 'Disabled by the operator on this deployment'
  }
  if (feature.deny_reason === 'not_implemented') return 'Not available on this deployment yet'
  if (!feature.allowed_by_config) return 'Disabled in this deployment configuration'
  if (!feature.available_on_host) return 'Backend planning runtime is not ready on this deployment'
  return 'Backend planning runtime is unavailable on this deployment'
}

function AppShell({ appTitle }: AppShellProps) {
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
  const ollamaOptions = advanced.getOptionsForRequest(
    effectiveThinkingEnabled ? reasoningLevel : false,
  )
  const session = useChatSession({
    selectedModel: models.selectedModel,
    userName,
    systemInstruction,
    planModeEnabled,
    themeStyle: appearance.themeStyle,
    ollamaOptions,
  })
  const gpu = useGpuStatus(session.isStreaming)
  const systemFeatures = useSystemFeatures('demo-public')
  const planModeFeature = systemFeatures.features?.workbench.plan_mode ?? null
  const planModeAvailable = !!planModeFeature?.effective_enabled
  const planModeAvailability = describePlanModeAvailability(planModeFeature)
  const desktopDiagnostics = useDesktopDiagnostics()
  const {
    handleDeleteAllHistory,
    handleDeleteConversation,
    handleRefreshHistory,
    handleRenameConversation,
    handleUploadEvent,
  } = useChatShellActions(session)

  useEffect(() => {
    document.title = appTitle
  }, [appTitle])

  useEffect(() => {
    setSidebarOpen(chatLayout.sidebarBehavior === 'docked')
  }, [chatLayout.sidebarBehavior])

  useEffect(() => {
    if (!planModeAvailable && planModeEnabled) {
      setPlanModeEnabled(false)
    }
  }, [planModeAvailable, planModeEnabled])

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
        onLoadHistorySession={sessionId => {
          void session.loadHistorySession(sessionId)
        }}
        onDeleteHistorySession={sessionId => {
          void session.deleteHistorySession(sessionId)
        }}
        onRefreshHistory={handleRefreshHistory}
        onDeleteAllHistory={handleDeleteAllHistory}
      />
      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        <TopBar
          sessionTitle={session.sessionTitle}
          hasSession={Boolean(session.sessionId)}
          modelCapabilities={models.capabilities?.capabilities ?? null}
          appearanceSummary={appearanceSummary}
          layoutMode={layoutMode}
          onSidebarToggle={() => setSidebarOpen(open => !open)}
          onOpenAppearance={() => setAppearanceOpen(true)}
          onRenameConversation={handleRenameConversation}
          thinkingEnabled={effectiveThinkingEnabled}
          desktopDiagnostics={desktopDiagnostics.diagnostics}
          desktopDiagnosticsError={desktopDiagnostics.error}
          systemInstruction={systemInstruction}
          onSystemInstructionChange={setSystemInstruction}
          onExportMarkdown={() =>
            downloadChatAsMarkdown(
              session.messages.filter(message => !message.hidden),
              session.sessionTitle,
            )
          }
          onDeleteConversation={handleDeleteConversation}
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
            personaStatusMessage={session.personaStatusMessage}
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
            codeSandboxFeature={systemFeatures.features?.code_sandbox ?? null}
            planModeEnabled={planModeEnabled}
            planModeAvailable={planModeAvailable}
            planModeAvailability={planModeAvailability}
            planModeFeature={planModeFeature}
            onPlanModeChange={setPlanModeEnabled}
            reasoningLevel={reasoningLevel}
            onReasoningLevelChange={setReasoningLevel}
            thinkingEnabled={effectiveThinkingEnabled}
            onThinkingEnabledChange={setThinkingEnabled}
          />
        </ErrorBoundary>
      </div>
      {appearanceOpen && (
        <Suspense fallback={null}>
          <LazyAppearancePanel
            open={appearanceOpen}
            appearance={appearance}
            effectiveMode={effectiveMode}
            onClose={() => setAppearanceOpen(false)}
            onChange={updateAppearance}
            onReset={resetAppearance}
          />
        </Suspense>
      )}
    </div>
  )
}

/** Root application: mount the public demo shell without any auth bootstrap. */
export default function App() {
  const branding = useBranding()

  useEffect(() => {
    void reportDesktopBootstrapStatus('ready')
  }, [])

  return <AppShell appTitle={branding.appTitle} />
}
