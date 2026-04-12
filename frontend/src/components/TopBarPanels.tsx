import type { ReactNode } from 'react'
import {
  AppearanceIcon,
  ChevronDownIcon,
  ChevronRightIcon,
} from './uiIcons'

export interface SettingsPanelProps {
  appearanceSummary: string
  advancedOpen: boolean
  apiKey: string
  ownerId: string
  systemInstruction: string
  temperature: number
  maxTokens: number
  topP: number
  onApiKeyChange: (value: string) => void
  onOwnerIdChange: (value: string) => void
  onSystemInstructionChange: (value: string) => void
  onAdvancedOpenChange: (open: boolean) => void
  onTemperatureChange: (value: number) => void
  onMaxTokensChange: (value: number) => void
  onTopPChange: (value: number) => void
  onResetAdvanced: () => void
  onOpenAppearance: () => void
  onClose: () => void
}

export interface ConversationActionsMenuProps {
  hasSession: boolean
  onRenameConversation: () => void
  onExportMarkdown: () => void
  onDeleteConversation: () => void
  onClose: () => void
  isNarrow: boolean
}

const MAX_INSTRUCTION_LEN = 1000
const MAX_AUTH_INPUT_LEN = 256

/** Upper bound for `max_tokens` in ChatRequest; must match backend `ChatRequest.max_tokens` le=. */
const API_MAX_GENERATION_TOKENS = 131_072

const fieldCls =
  'w-full cursor-text select-text rounded-xl px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-sky-500/35'
const actionButtonCls =
  'flex w-full items-center justify-between rounded-xl px-2.5 py-2 text-left text-[13px] transition-colors hover:bg-slate-900/[0.04]'

function clampGenerationValue(value: number, minimum: number, maximum: number): number {
  return Math.min(maximum, Math.max(minimum, value))
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

function ProtectedAccessSection({
  apiKey,
  ownerId,
  onApiKeyChange,
  onOwnerIdChange,
}: Pick<
  SettingsPanelProps,
  'apiKey' | 'ownerId' | 'onApiKeyChange' | 'onOwnerIdChange'
>) {
  return (
    <section className="border-t pt-3" style={{ borderColor: 'var(--border-color)' }}>
      <div className="mb-2">
        <p
          className="text-[11px] font-semibold uppercase tracking-[0.08em]"
          style={{ color: 'var(--text-muted)' }}
        >
          Protected access
        </p>
        <p className="mt-1 text-xs" style={{ color: 'var(--text-muted)' }}>
          Saved only in this browser and attached as protected API headers.
        </p>
      </div>
      <div className="grid grid-cols-1 gap-2">
        <div>
          <label
            htmlFor="goat-api-key"
            className="mb-1 block text-[11px] font-medium"
            style={{ color: 'var(--text-muted)' }}
          >
            API key
          </label>
          <input
            id="goat-api-key"
            type="password"
            autoComplete="off"
            maxLength={MAX_AUTH_INPUT_LEN}
            value={apiKey}
            onChange={event => onApiKeyChange(event.target.value)}
            placeholder="Optional secret for protected APIs"
            className={fieldCls}
            style={{
              background: 'var(--input-bg)',
              border: '1px solid var(--input-border)',
              color: 'var(--text-main)',
            }}
          />
        </div>
        <div>
          <label
            htmlFor="goat-owner-id"
            className="mb-1 block text-[11px] font-medium"
            style={{ color: 'var(--text-muted)' }}
          >
            Owner ID
          </label>
          <input
            id="goat-owner-id"
            type="text"
            autoComplete="off"
            maxLength={MAX_AUTH_INPUT_LEN}
            value={ownerId}
            onChange={event => onOwnerIdChange(event.target.value)}
            placeholder="Optional owner for protected chat/history"
            className={fieldCls}
            style={{
              background: 'var(--input-bg)',
              border: '1px solid var(--input-border)',
              color: 'var(--text-main)',
            }}
          />
        </div>
      </div>
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

export function ConversationActionsMenu({
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

export function SettingsPanel({
  appearanceSummary,
  advancedOpen,
  apiKey,
  ownerId,
  systemInstruction,
  temperature,
  maxTokens,
  topP,
  onApiKeyChange,
  onOwnerIdChange,
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
        <ProtectedAccessSection
          apiKey={apiKey}
          ownerId={ownerId}
          onApiKeyChange={onApiKeyChange}
          onOwnerIdChange={onOwnerIdChange}
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
