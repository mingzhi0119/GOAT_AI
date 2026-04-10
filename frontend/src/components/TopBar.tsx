import { useEffect, useRef, useState, type FC, type ReactNode } from 'react'
import type { ChatLayoutMode } from '../utils/chatLayout'
import {
  AppearanceIcon,
  ChevronDownIcon,
  ChevronRightIcon,
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

interface SettingsPanelProps {
  appearanceSummary: string
  advancedOpen: boolean
  systemInstruction: string
  temperature: number
  maxTokens: number
  topP: number
  onSystemInstructionChange: (value: string) => void
  onAdvancedOpenChange: (open: boolean) => void
  onTemperatureChange: (value: number) => void
  onMaxTokensChange: (value: number) => void
  onTopPChange: (value: number) => void
  onResetAdvanced: () => void
  onOpenAppearance: () => void
  onClose: () => void
}

interface ConversationActionsMenuProps {
  hasSession: boolean
  onRenameConversation: () => void
  onExportMarkdown: () => void
  onDeleteConversation: () => void
  onClose: () => void
  isNarrow: boolean
}

const MAX_INSTRUCTION_LEN = 1000

/** Upper bound for `max_tokens` in ChatRequest; must match backend `ChatRequest.max_tokens` le=. */
const API_MAX_GENERATION_TOKENS = 131_072

const fieldCls =
  'w-full cursor-text select-text rounded-xl px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-sky-500/35'
const actionButtonCls =
  'flex w-full items-center justify-between rounded-xl px-2.5 py-2 text-left text-[13px] transition-colors hover:bg-slate-900/[0.04]'

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

function ConversationActionsMenu({
  hasSession,
  onRenameConversation,
  onExportMarkdown,
  onDeleteConversation,
  onClose,
  isNarrow,
}: ConversationActionsMenuProps) {
  return (
    <div
      className={`absolute right-0 top-full z-50 mt-2 rounded-2xl border p-1.5 shadow-[0_10px_20px_rgba(15,23,42,0.08)] ${isNarrow ? 'w-[min(92vw,20rem)]' : 'w-[332px]'}`}
      style={{
        borderColor: 'var(--input-border)',
        background: 'var(--composer-menu-bg)',
        backdropFilter: 'blur(14px)',
        boxShadow: '0 10px 20px rgba(15,23,42,0.08)',
      }}
      role="menu"
      aria-label="Conversation actions"
      onClick={event => event.stopPropagation()}
    >
      <button
        type="button"
        role="menuitem"
        disabled={!hasSession}
        className={`${actionButtonCls} ${hasSession ? '' : 'cursor-not-allowed opacity-50'}`}
        style={{ color: hasSession ? 'var(--text-main)' : 'var(--text-muted)' }}
        onClick={() => {
          if (!hasSession) return
          onRenameConversation()
          onClose()
        }}
      >
        <span>
          <span className="block font-medium leading-none">Rename</span>
          <span className="block pt-1 text-xs" style={{ color: 'var(--text-muted)' }}>
            Change the current conversation title
          </span>
        </span>
      </button>
      <button
        type="button"
        role="menuitem"
        className={actionButtonCls}
        style={{ color: 'var(--text-main)' }}
        onClick={() => {
          onExportMarkdown()
          onClose()
        }}
      >
        <span>
          <span className="block font-medium leading-none">Export to Markdown</span>
          <span className="block pt-1 text-xs" style={{ color: 'var(--text-muted)' }}>
            Save the current conversation as a Markdown file
          </span>
        </span>
      </button>
      <button
        type="button"
        role="menuitem"
        disabled={!hasSession}
        className={`${actionButtonCls} mt-0.5 ${hasSession ? '' : 'cursor-not-allowed opacity-50'}`}
        style={{ color: hasSession ? 'var(--text-main)' : 'var(--text-muted)' }}
        onClick={() => {
          if (!hasSession) return
          onDeleteConversation()
          onClose()
        }}
      >
        <span>
          <span className="block font-medium leading-none">Delete</span>
          <span className="block pt-1 text-xs" style={{ color: 'var(--text-muted)' }}>
            Remove this saved conversation
          </span>
        </span>
      </button>
    </div>
  )
}

function InstructionsSection({
  systemInstruction,
  onSystemInstructionChange,
}: Pick<SettingsPanelProps, 'systemInstruction' | 'onSystemInstructionChange'>) {
  return (
    <section className="space-y-2">
      <div className="flex items-center justify-between gap-3">
        <p
          className="text-[11px] font-semibold uppercase tracking-[0.08em]"
          style={{ color: 'var(--text-muted)' }}
        >
          Instructions
        </p>
        <button
          type="button"
          className="rounded-full border px-2.5 py-1 text-[11px]"
          style={{
            borderColor: 'var(--border-color)',
            color: 'var(--text-muted)',
          }}
          onClick={() => onSystemInstructionChange('')}
        >
          Clear
        </button>
      </div>
      <textarea
        id="goat-system-instruction"
        rows={3}
        maxLength={MAX_INSTRUCTION_LEN}
        value={systemInstruction}
        onChange={event => onSystemInstructionChange(event.target.value)}
        placeholder="Optional: tone, format, or constraints for the model"
        className={`${fieldCls} min-h-[4.5rem] resize-y`}
        style={{
          background: 'var(--input-bg)',
          border: '1px solid var(--input-border)',
          color: 'var(--text-main)',
        }}
      />
      <p className="mt-1 text-right text-[10px]" style={{ color: 'var(--text-muted)' }}>
        {systemInstruction.length}/{MAX_INSTRUCTION_LEN}
      </p>
    </section>
  )
}

function GenerationField({
  label,
  input,
}: {
  label: string
  input: ReactNode
}) {
  return (
    <div>
      <label
        className="mb-1 block text-[11px] font-medium"
        style={{ color: 'var(--text-muted)' }}
      >
        {label}
      </label>
      {input}
    </div>
  )
}

function GenerationSettingsSection({
  advancedOpen,
  temperature,
  maxTokens,
  topP,
  onAdvancedOpenChange,
  onTemperatureChange,
  onMaxTokensChange,
  onTopPChange,
  onResetAdvanced,
}: Pick<
  SettingsPanelProps,
  | 'advancedOpen'
  | 'temperature'
  | 'maxTokens'
  | 'topP'
  | 'onAdvancedOpenChange'
  | 'onTemperatureChange'
  | 'onMaxTokensChange'
  | 'onTopPChange'
  | 'onResetAdvanced'
>) {
  return (
    <section className="border-t pt-3" style={{ borderColor: 'var(--border-color)' }}>
      <div className="mb-2 flex items-start justify-between gap-3">
        <button
          type="button"
          className="flex items-start gap-2 text-left"
          aria-expanded={advancedOpen}
          onClick={() => onAdvancedOpenChange(!advancedOpen)}
        >
          <span
            className="mt-[1px] inline-flex h-4 w-4 items-center justify-center"
            style={{ color: 'var(--text-muted)' }}
          >
            {advancedOpen ? <ChevronDownIcon /> : <ChevronRightIcon />}
          </span>
          <span>
            <span
              className="block text-[11px] font-semibold uppercase tracking-[0.08em]"
              style={{ color: 'var(--text-muted)' }}
            >
              Generation
            </span>
            <span className="mt-1 block text-xs" style={{ color: 'var(--text-muted)' }}>
              Tune generation behavior for this chat.
            </span>
          </span>
        </button>
        <button
          type="button"
          className="rounded-full border px-2.5 py-1 text-[11px]"
          style={{
            borderColor: 'var(--border-color)',
            color: 'var(--text-muted)',
          }}
          aria-label="Reset generation settings to defaults"
          onClick={() => {
            onResetAdvanced()
            onAdvancedOpenChange(true)
          }}
        >
          Reset
        </button>
      </div>
      {advancedOpen && (
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
          <GenerationField
            label="Temperature"
            input={
              <input
                type="number"
                step={0.05}
                min={0}
                max={2}
                value={temperature}
                onChange={event => {
                  const value = Number.parseFloat(event.target.value)
                  if (!Number.isNaN(value)) {
                    onTemperatureChange(clampGenerationValue(value, 0, 2))
                  }
                }}
                className={fieldCls}
                style={{
                  background: 'var(--input-bg)',
                  border: '1px solid var(--input-border)',
                  color: 'var(--text-main)',
                }}
              />
            }
          />
          <GenerationField
            label="Max tokens"
            input={
              <input
                type="number"
                step={1}
                min={1}
                value={maxTokens}
                onChange={event => {
                  const value = Number.parseInt(event.target.value, 10)
                  if (!Number.isNaN(value)) {
                    onMaxTokensChange(
                      clampGenerationValue(value, 1, API_MAX_GENERATION_TOKENS),
                    )
                  }
                }}
                className={fieldCls}
                style={{
                  background: 'var(--input-bg)',
                  border: '1px solid var(--input-border)',
                  color: 'var(--text-main)',
                }}
              />
            }
          />
          <GenerationField
            label="Top P"
            input={
              <input
                type="number"
                step={0.05}
                min={0}
                max={1}
                value={topP}
                onChange={event => {
                  const value = Number.parseFloat(event.target.value)
                  if (!Number.isNaN(value)) {
                    onTopPChange(clampGenerationValue(value, 0, 1))
                  }
                }}
                className={fieldCls}
                style={{
                  background: 'var(--input-bg)',
                  border: '1px solid var(--input-border)',
                  color: 'var(--text-main)',
                }}
              />
            }
          />
        </div>
      )}
    </section>
  )
}

function AppearanceSection({
  appearanceSummary,
  onOpenAppearance,
  onClose,
}: Pick<SettingsPanelProps, 'appearanceSummary' | 'onOpenAppearance' | 'onClose'>) {
  return (
    <section className="border-t pt-3" style={{ borderColor: 'var(--border-color)' }}>
      <p
        className="text-[11px] font-semibold uppercase tracking-[0.08em]"
        style={{ color: 'var(--text-muted)' }}
      >
        Appearance
      </p>
      <button
        type="button"
        className="mt-1.5 flex w-full items-center justify-between rounded-2xl px-2 py-1.5 text-left text-sm transition-colors hover:bg-slate-900/[0.04]"
        style={{ color: 'var(--text-main)' }}
        onClick={() => {
          onOpenAppearance()
          onClose()
        }}
      >
        <span className="inline-flex items-center gap-2">
          <AppearanceIcon />
          <span>Open Appearance</span>
        </span>
        <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
          {appearanceSummary}
        </span>
      </button>
    </section>
  )
}

function SettingsPanel({
  appearanceSummary,
  advancedOpen,
  systemInstruction,
  temperature,
  maxTokens,
  topP,
  onSystemInstructionChange,
  onAdvancedOpenChange,
  onTemperatureChange,
  onMaxTokensChange,
  onTopPChange,
  onResetAdvanced,
  onOpenAppearance,
  onClose,
}: SettingsPanelProps) {
  return (
    <div
      className="absolute right-0 z-50 mt-2 max-h-[min(85vh,38rem)] overflow-y-auto rounded-[24px] border px-4 py-3 shadow-[0_16px_36px_var(--panel-shadow-color)] w-[min(92vw,26rem)]"
      style={{
        background: 'var(--composer-menu-bg-strong)',
        borderColor: 'var(--input-border)',
        color: 'var(--text-main)',
        backdropFilter: 'blur(18px)',
      }}
      role="dialog"
      aria-label="Settings"
      onClick={event => event.stopPropagation()}
    >
      <div className="space-y-3">
        <InstructionsSection
          systemInstruction={systemInstruction}
          onSystemInstructionChange={onSystemInstructionChange}
        />
        <GenerationSettingsSection
          advancedOpen={advancedOpen}
          temperature={temperature}
          maxTokens={maxTokens}
          topP={topP}
          onAdvancedOpenChange={onAdvancedOpenChange}
          onTemperatureChange={onTemperatureChange}
          onMaxTokensChange={onMaxTokensChange}
          onTopPChange={onTopPChange}
          onResetAdvanced={onResetAdvanced}
        />
        <AppearanceSection
          appearanceSummary={appearanceSummary}
          onOpenAppearance={onOpenAppearance}
          onClose={onClose}
        />
      </div>
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
