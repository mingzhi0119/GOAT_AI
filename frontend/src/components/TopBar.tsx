import { useEffect, useRef, useState, type FC } from 'react'
import type { DesktopDiagnostics } from '../api/types'
import type { ChatLayoutMode } from '../utils/chatLayout'
import { ConversationActionsMenu, SettingsPanel } from './TopBarPanels'
import {
  MoreIcon,
  SettingsIcon,
  SidebarToggleIcon,
} from './uiIcons'

interface Props {
  sessionTitle: string | null
  hasSession: boolean
  modelCapabilities: string[] | null
  appearanceSummary: string
  layoutMode?: ChatLayoutMode
  onSidebarToggle?: () => void
  onOpenAppearance: () => void
  onRenameConversation: () => void
  thinkingEnabled?: boolean
  desktopDiagnostics?: DesktopDiagnostics | null
  desktopDiagnosticsError?: string | null
  apiKey: string
  ownerId: string
  onApiKeyChange: (value: string) => void
  onOwnerIdChange: (value: string) => void
  systemInstruction: string
  onSystemInstructionChange: (value: string) => void
  onExportMarkdown: () => void
  onDeleteConversation: () => void
  advancedOpen: boolean
  onAdvancedOpenChange: (open: boolean) => void
  temperature: number
  onTemperatureChange: (v: number) => void
  maxTokens: number
  onMaxTokensChange: (v: number) => void
  topP: number
  onTopPChange: (v: number) => void
  onResetAdvanced: () => void
}

interface CapabilityItem {
  key: string
  label: string
  active: boolean
}

function formatSkillLabel(capability: string): string | null {
  const normalized = capability.trim().toLowerCase()
  if (!normalized || normalized === 'completion') return null
  if (normalized === 'thinking') return 'Thinking'
  if (normalized === 'tools' || normalized === 'tool_calling') return 'Tools'
  if (normalized === 'vision') return 'Vision'
  if (normalized === 'audio' || normalized === 'sound' || normalized === 'speech') return 'Sound'
  if (normalized === 'images' || normalized === 'image') return 'Vision'
  return normalized
    .split(/[_\s-]+/)
    .filter(Boolean)
    .map(part => part[0]!.toUpperCase() + part.slice(1).toLowerCase())
    .join(' ')
}

const CAPABILITY_PRIORITY: Record<string, number> = {
  Thinking: 0,
  Vision: 1,
  Tools: 2,
}

function buildCapabilityItems(
  modelCapabilities: string[] | null,
  thinkingEnabled: boolean,
): CapabilityItem[] {
  const labels = (modelCapabilities ?? []).map(formatSkillLabel).filter(
    (label): label is string => Boolean(label),
  )
  const uniqueLabels = Array.from(new Set(labels))
  return uniqueLabels
    .sort((left, right) => {
      const leftRank = CAPABILITY_PRIORITY[left] ?? 99
      const rightRank = CAPABILITY_PRIORITY[right] ?? 99
      if (leftRank !== rightRank) return leftRank - rightRank
      return left.localeCompare(right)
    })
    .map(label => ({
      key: label,
      label,
      active: label === 'Thinking' ? thinkingEnabled : false,
    }))
}

function clampGenerationValue(value: number, minimum: number, maximum: number): number {
  return Math.min(maximum, Math.max(minimum, value))
}

function CapabilityBadge({
  item,
  includeTestId = true,
}: {
  item: CapabilityItem
  includeTestId?: boolean
}) {
  return (
    <span
      data-testid={includeTestId ? 'model-capability-badge' : undefined}
      data-capability={item.label}
      className="inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium"
      style={{
        borderColor: item.active ? 'var(--theme-accent)' : 'var(--border-color)',
        color: item.active ? 'var(--theme-accent-contrast)' : 'var(--text-main)',
        background: item.active ? 'var(--theme-accent)' : 'var(--composer-muted-surface)',
      }}
    >
      {item.label}
    </span>
  )
}

function CapabilityBadges({
  capabilityItems,
  isNarrow,
}: {
  capabilityItems: CapabilityItem[]
  isNarrow: boolean
}) {
  if (capabilityItems.length === 0) return null

  const visibleCapabilities = isNarrow ? capabilityItems.slice(0, 2) : capabilityItems
  const hiddenCapabilities = isNarrow ? capabilityItems.slice(2) : []
  const capabilitySummary = capabilityItems.map(item => item.label).join(' / ')

  return (
    <div
      className="group/caps relative flex min-w-0 items-start gap-1.5 select-none"
      aria-label={`Model capabilities: ${capabilitySummary}`}
    >
      <div
        className={`flex min-w-0 ${isNarrow ? 'items-center gap-1' : 'flex-wrap items-center gap-1.5'}`}
      >
        {visibleCapabilities.map(item => (
          <CapabilityBadge key={item.key} item={item} />
        ))}
      </div>
      {isNarrow && hiddenCapabilities.length > 0 && (
        <div
          role="tooltip"
          className="pointer-events-none absolute left-0 top-full z-50 mt-2 hidden min-w-[12rem] rounded-2xl border p-2 text-left shadow-[0_12px_24px_rgba(15,23,42,0.14)] group-hover/caps:block group-focus-within/caps:block"
          style={{
            borderColor: 'var(--input-border)',
            background: 'var(--composer-menu-bg-strong)',
          }}
        >
          <p
            className="mb-1 text-[10px] font-semibold uppercase tracking-[0.08em]"
            style={{ color: 'var(--text-muted)' }}
          >
            More capabilities
          </p>
          <div className="flex flex-wrap gap-1.5">
            {capabilityItems.map(item => (
              <CapabilityBadge key={item.key} item={item} includeTestId={false} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

const TopBar: FC<Props> = ({
  sessionTitle,
  hasSession,
  modelCapabilities,
  appearanceSummary,
  layoutMode = 'wide',
  onSidebarToggle,
  onOpenAppearance,
  onRenameConversation,
  thinkingEnabled = false,
  desktopDiagnostics = null,
  desktopDiagnosticsError = null,
  apiKey,
  ownerId,
  onApiKeyChange,
  onOwnerIdChange,
  systemInstruction,
  onSystemInstructionChange,
  onExportMarkdown,
  onDeleteConversation,
  advancedOpen,
  onAdvancedOpenChange,
  temperature,
  onTemperatureChange,
  maxTokens,
  onMaxTokensChange,
  topP,
  onTopPChange,
  onResetAdvanced,
}) => {
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [actionsOpen, setActionsOpen] = useState(false)
  const wrapRef = useRef<HTMLDivElement>(null)
  const isNarrow = layoutMode === 'narrow'
  const capabilityItems = buildCapabilityItems(modelCapabilities, thinkingEnabled)

  useEffect(() => {
    const closeMenus = (event: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(event.target as Node)) {
        setSettingsOpen(false)
        setActionsOpen(false)
      }
    }
    document.addEventListener('click', closeMenus)
    return () => document.removeEventListener('click', closeMenus)
  }, [])

  return (
    <header
      className={`z-20 flex h-12 flex-shrink-0 items-center ${isNarrow ? 'gap-2 px-2.5' : 'px-3'}`}
      style={{ background: 'var(--bg-chat)' }}
    >
      {isNarrow ? (
        <button
          type="button"
          aria-label="Open sidebar"
          className="inline-flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full transition-all hover:opacity-90"
          style={{
            color: 'var(--text-main)',
            background: 'var(--composer-muted-surface)',
          }}
          onClick={onSidebarToggle}
        >
          <SidebarToggleIcon />
        </button>
      ) : (
        <div className="hidden" aria-hidden="true" />
      )}

      <div className="flex min-w-0 flex-1 items-center gap-3 px-1 select-none">
        <h1
          className="max-w-full cursor-default truncate text-left text-sm font-medium select-none"
          style={{ color: 'var(--text-main)' }}
          title={sessionTitle ?? undefined}
        >
          {sessionTitle ?? 'New conversation'}
        </h1>
        <CapabilityBadges capabilityItems={capabilityItems} isNarrow={isNarrow} />
      </div>

      <div className="flex min-w-0 flex-shrink-0 justify-end" ref={wrapRef}>
        <div className="relative flex items-center gap-2">
          <button
            type="button"
            className="inline-flex h-9 w-9 items-center justify-center rounded-lg transition-colors hover:bg-[var(--composer-muted-surface)]"
            style={{ color: 'var(--text-main)' }}
            aria-label="Conversation actions"
            aria-expanded={actionsOpen}
            aria-haspopup="menu"
            onClick={event => {
              event.stopPropagation()
              setActionsOpen(open => !open)
              setSettingsOpen(false)
            }}
          >
            <MoreIcon />
          </button>
          {actionsOpen && (
            <ConversationActionsMenu
              hasSession={hasSession}
              onRenameConversation={onRenameConversation}
              onExportMarkdown={onExportMarkdown}
              onDeleteConversation={onDeleteConversation}
              onClose={() => setActionsOpen(false)}
              isNarrow={isNarrow}
            />
          )}

          <div className="relative">
            <button
              type="button"
              className="inline-flex h-9 w-9 items-center justify-center rounded-lg transition-colors hover:bg-[var(--composer-muted-surface)]"
              style={{ color: 'var(--text-main)' }}
              aria-label="Settings"
              aria-expanded={settingsOpen}
              aria-haspopup="dialog"
              onClick={event => {
                event.stopPropagation()
                setSettingsOpen(open => !open)
                setActionsOpen(false)
              }}
            >
              <SettingsIcon />
            </button>

            {settingsOpen && (
              <SettingsPanel
                appearanceSummary={appearanceSummary}
                advancedOpen={advancedOpen}
                desktopDiagnostics={desktopDiagnostics}
                desktopDiagnosticsError={desktopDiagnosticsError}
                apiKey={apiKey}
                ownerId={ownerId}
                onApiKeyChange={onApiKeyChange}
                onOwnerIdChange={onOwnerIdChange}
                systemInstruction={systemInstruction}
                temperature={temperature}
                maxTokens={maxTokens}
                topP={topP}
                onSystemInstructionChange={onSystemInstructionChange}
                onAdvancedOpenChange={onAdvancedOpenChange}
                onTemperatureChange={onTemperatureChange}
                onMaxTokensChange={onMaxTokensChange}
                onTopPChange={onTopPChange}
                onResetAdvanced={onResetAdvanced}
                onOpenAppearance={onOpenAppearance}
                onClose={() => setSettingsOpen(false)}
              />
            )}
          </div>
        </div>
      </div>
    </header>
  )
}

export default TopBar
