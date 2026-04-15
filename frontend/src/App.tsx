import { Suspense, lazy, useEffect, useMemo, useState } from 'react'
import type { BrowserAuthSession, RuntimeFeature } from './api/types'
import ChatWindow from './components/ChatWindow'
import BrowserLoginGate from './components/BrowserLoginGate'
import { ErrorBoundary } from './components/ErrorBoundary'
import Sidebar from './components/Sidebar'
import TopBar from './components/TopBar'
import { useBranding } from './config/branding'
import { useAdvancedSettings } from './hooks/useAdvancedSettings'
import { useAppearance } from './hooks/useAppearance'
import { useApiKey } from './hooks/useApiKey'
import { useBrowserAccessAuth } from './hooks/useBrowserAccessAuth'
import { useChatLayoutMode } from './hooks/useChatLayoutMode'
import { useChatSession } from './hooks/useChatSession'
import { useChatShellActions } from './hooks/useChatShellActions'
import { useDesktopDiagnostics } from './hooks/useDesktopDiagnostics'
import { useGpuStatus } from './hooks/useGpuStatus'
import { useModels } from './hooks/useModels'
import { useOwnerId } from './hooks/useOwnerId'
import { useSystemFeatures } from './hooks/useSystemFeatures'
import { useSystemInstruction } from './hooks/useSystemInstruction'
import { useUserName } from './hooks/useUserName'
import { reportDesktopBootstrapStatus } from './utils/desktopBootstrap'
import { downloadChatAsMarkdown } from './utils/exportChatMarkdown'
import { getChatLayoutDecisions } from './utils/chatLayout'

const LazyAppearancePanel = lazy(() => import('./components/AppearancePanel'))

interface AppShellProps {
  appTitle: string
  browserAuthSession: BrowserAuthSession | null
  isSigningOut: boolean
  onLogout: () => Promise<void>
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

function FullscreenStatus({
  title,
  message,
  isBusy,
  onRetry,
}: {
  title: string
  message: string
  isBusy?: boolean
  onRetry: () => Promise<void>
}) {
  return (
    <div
      className="flex min-h-screen items-center justify-center px-4"
      style={{ background: 'var(--bg-main)' }}
    >
      <div
        className="w-full max-w-md rounded-[28px] border px-6 py-7 shadow-[0_18px_48px_var(--panel-shadow-color)]"
        style={{
          background: 'var(--composer-menu-bg-strong)',
          borderColor: 'var(--input-border)',
          color: 'var(--text-main)',
          backdropFilter: 'blur(18px)',
        }}
      >
        <p
          className="text-xs font-semibold uppercase tracking-[0.1em]"
          style={{ color: 'var(--text-muted)' }}
        >
          GOAT AI desktop
        </p>
        <h1 className="mt-2 text-2xl font-semibold tracking-[-0.03em]">{title}</h1>
        <p className="mt-3 text-sm leading-6" style={{ color: 'var(--text-muted)' }}>
          {message}
        </p>
        <button
          type="button"
          className="mt-6 rounded-2xl border px-4 py-3 text-sm"
          style={{
            borderColor: 'var(--input-border)',
            color: 'var(--text-main)',
            opacity: isBusy ? 0.7 : 1,
          }}
          onClick={() => {
            void onRetry()
          }}
          disabled={isBusy}
        >
          {isBusy ? 'Checking...' : 'Retry'}
        </button>
      </div>
    </div>
  )
}

function AppShell({
  appTitle,
  browserAuthSession,
  isSigningOut,
  onLogout,
}: AppShellProps) {
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
  const { apiKey, setApiKey } = useApiKey()
  const { ownerId, setOwnerId } = useOwnerId()
  const { userName, setUserName } = useUserName()
  const { systemInstruction, setSystemInstruction } = useSystemInstruction()
  const systemFeatureRefreshKey = `${apiKey}\n${ownerId}`
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
  const systemFeatures = useSystemFeatures(systemFeatureRefreshKey)
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
          apiKey={apiKey}
          ownerId={ownerId}
          onApiKeyChange={setApiKey}
          onOwnerIdChange={setOwnerId}
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
          browserAuthSession={browserAuthSession}
          isSigningOut={isSigningOut}
          onLogout={onLogout}
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

/** Root application: bootstrap browser auth first, then mount the shell. */
export default function App() {
  const branding = useBranding()
  const auth = useBrowserAccessAuth()
  const bootstrapStatus =
    auth.isLoading && auth.session === null
      ? 'pending'
      : auth.session === null
        ? 'failed'
        : 'ready'

  useEffect(() => {
    if (bootstrapStatus === 'pending') return
    void reportDesktopBootstrapStatus(bootstrapStatus)
  }, [bootstrapStatus])

  if (auth.isLoading && auth.session === null) {
    return (
      <FullscreenStatus
        title={branding.appTitle}
        message="Checking browser access for this deployment."
        isBusy={true}
        onRetry={auth.refresh}
      />
    )
  }

  if (auth.session?.auth_required && !auth.session.authenticated) {
    return (
      <BrowserLoginGate
        appTitle={branding.appTitle}
        session={auth.session}
        isLoading={auth.isLoading}
        isSubmitting={auth.isSubmitting}
        error={auth.error}
        onLoginShared={auth.loginShared}
        onLoginAccount={auth.loginAccount}
        onStartGoogleLogin={auth.startGoogleLogin}
        onRetry={auth.refresh}
      />
    )
  }

  if (auth.session === null) {
    return (
      <FullscreenStatus
        title={branding.appTitle}
        message={auth.error ?? 'Unable to load this deployment right now.'}
        onRetry={auth.refresh}
      />
    )
  }

  return (
    <AppShell
      key={auth.shellKey}
      appTitle={branding.appTitle}
      browserAuthSession={auth.session}
      isSigningOut={auth.isSubmitting}
      onLogout={auth.logout}
    />
  )
}
