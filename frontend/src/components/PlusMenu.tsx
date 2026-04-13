import {
  useCallback,
  useEffect,
  useRef,
  type CSSProperties,
  type KeyboardEvent,
  type RefObject,
} from 'react'
import type { CodeSandboxFeature, RuntimeFeature } from '../api/types'
import {
  ChevronRightIcon,
  CodeSandboxIcon,
  ManageIcon,
  PlanModeIcon,
  ThinkingModeIcon,
  UploadIcon,
} from './chatComposerPrimitives'

interface PlusMenuProps {
  isOpen: boolean
  isNarrow: boolean
  panelId?: string
  triggerRef?: RefObject<HTMLButtonElement | null>
  codeSandboxFeature: CodeSandboxFeature | null
  planModeEnabled: boolean
  planModeAvailability?: string
  planModeFeature?: RuntimeFeature | null
  supportsThinking: boolean
  thinkingEnabled: boolean
  onClose: () => void
  onOpenCodeSandbox: () => void
  onUploadFiles: () => void
  onOpenManageUploads: () => void
  onTogglePlanMode: () => void
  onToggleThinkingMode: () => void
}

const menuStyle = {
  borderColor: 'var(--input-border)',
  background: 'var(--composer-menu-bg)',
  backdropFilter: 'blur(14px)',
  boxShadow: '0 10px 20px rgba(15,23,42,0.08)',
} satisfies CSSProperties

export default function PlusMenu({
  isOpen,
  isNarrow,
  panelId,
  triggerRef,
  codeSandboxFeature,
  planModeEnabled,
  planModeAvailability,
  planModeFeature,
  supportsThinking,
  thinkingEnabled,
  onClose,
  onOpenCodeSandbox,
  onUploadFiles,
  onOpenManageUploads,
  onTogglePlanMode,
  onToggleThinkingMode,
}: PlusMenuProps) {
  const firstActionRef = useRef<HTMLButtonElement | null>(null)

  const restoreTriggerFocus = useCallback(() => {
    window.setTimeout(() => triggerRef?.current?.focus(), 0)
  }, [triggerRef])

  useEffect(() => {
    if (!isOpen) return
    const timer = window.setTimeout(() => firstActionRef.current?.focus(), 0)
    return () => window.clearTimeout(timer)
  }, [isOpen])

  if (!isOpen) return null

  const planModeCapabilityKnown = planModeFeature !== undefined
  const planModeAvailable = planModeFeature
    ? !!planModeFeature.effective_enabled
    : !planModeCapabilityKnown
  const codeSandboxEnabled =
    !!codeSandboxFeature?.policy_allowed && !!codeSandboxFeature?.effective_enabled
  const localhostFallback = codeSandboxFeature?.provider_name === 'localhost'
  const codeSandboxReason = !codeSandboxFeature
    ? 'Checking availability'
    : !codeSandboxFeature.policy_allowed
      ? 'Not available for this API key'
      : !codeSandboxFeature.effective_enabled
        ? codeSandboxFeature.deny_reason === 'docker_unavailable'
          ? 'Docker runtime is not ready on this deployment'
          : codeSandboxFeature.deny_reason === 'localhost_unavailable'
            ? 'Local shell runtime is not ready on this deployment'
          : codeSandboxFeature.deny_reason === 'disabled_by_operator'
            ? 'Disabled by the operator on this deployment'
            : 'Runtime is not available on this deployment'
        : localhostFallback
          ? 'Run a short shell snippet on the local host shell (trusted-dev fallback)'
          : 'Run a short shell snippet in an isolated, no-network sandbox'
  const planModeReason =
    planModeAvailability ??
    (planModeAvailable
      ? 'Backend planning runtime is ready for this caller'
      : 'Checking backend planning readiness')

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key !== 'Escape') return
    event.preventDefault()
    onClose()
    restoreTriggerFocus()
  }

  return (
    <div
      id={panelId}
      className={`absolute bottom-14 left-0 z-30 rounded-2xl border p-1.5 shadow-[0_10px_20px_rgba(15,23,42,0.08)] ${isNarrow ? 'w-[min(92vw,20rem)]' : 'w-[332px]'}`}
      style={menuStyle}
      role="dialog"
      aria-label="Upload and planning actions"
      onPointerDown={event => event.stopPropagation()}
      onKeyDown={handleKeyDown}
    >
      <button
        ref={firstActionRef}
        type="button"
        onClick={() => {
          onUploadFiles()
          onClose()
        }}
        className="flex w-full items-center rounded-xl px-2.5 py-2 text-left text-[13px] transition-colors hover:bg-slate-900/[0.04]"
        style={{ color: 'var(--text-main)' }}
      >
        <span className="inline-flex items-center gap-2.5">
          <span className="inline-flex h-4 w-4 items-center justify-center">
            <UploadIcon />
          </span>
          <span>
            <span className="block font-medium leading-none">Upload Files</span>
            <span className="block text-xs" style={{ color: 'var(--text-muted)' }}>
              Add images or knowledge files
            </span>
          </span>
        </span>
      </button>

      <button
        type="button"
        onClick={() => {
          if (!codeSandboxEnabled) return
          onOpenCodeSandbox()
        }}
        disabled={!codeSandboxEnabled}
        className="mt-0.5 flex w-full items-center justify-between rounded-xl px-2.5 py-2 text-left text-[13px] transition-colors hover:bg-slate-900/[0.04] disabled:cursor-not-allowed disabled:opacity-70"
        style={{ color: 'var(--text-main)' }}
        aria-label={
          codeSandboxEnabled
            ? 'Open code sandbox'
            : `Code sandbox unavailable: ${codeSandboxReason}`
        }
      >
        <span className="inline-flex items-center gap-2.5">
          <span className="inline-flex h-4 w-4 items-center justify-center">
            <CodeSandboxIcon />
          </span>
          <span>
            <span className="block font-medium leading-none">Run Code</span>
            <span className="block text-xs" style={{ color: 'var(--text-muted)' }}>
              {codeSandboxReason}
            </span>
          </span>
        </span>
        <ChevronRightIcon className="h-[18px] w-[18px] shrink-0" />
      </button>

      <button
        type="button"
        onClick={onOpenManageUploads}
        className="mt-0.5 flex w-full items-center justify-between rounded-xl px-2.5 py-2 text-left text-[13px] transition-colors hover:bg-slate-900/[0.04]"
        style={{ color: 'var(--text-main)' }}
      >
        <span className="inline-flex items-center gap-2.5">
          <span className="inline-flex h-4 w-4 items-center justify-center">
            <ManageIcon />
          </span>
          <span>
            <span className="block font-medium leading-none">Manage Uploads</span>
            <span className="block text-xs" style={{ color: 'var(--text-muted)' }}>
              Review files and inclusion modes
            </span>
          </span>
        </span>
        <ChevronRightIcon className="h-[18px] w-[18px] shrink-0" />
      </button>

      <div
        className="mt-0.5 flex items-center justify-between rounded-xl px-2.5 py-2"
        style={{ color: 'var(--text-main)' }}
      >
        <span className="inline-flex items-center gap-2.5">
          <span className="inline-flex h-4 w-4 items-center justify-center">
            <PlanModeIcon />
          </span>
          <span>
            <span className="block text-[13px] font-medium leading-none">Plan Mode</span>
            <span className="block text-xs" style={{ color: 'var(--text-muted)' }}>
              {planModeReason}
            </span>
          </span>
        </span>
        <button
          type="button"
          role="switch"
          aria-label={
            planModeAvailable ? 'Plan mode' : `Plan mode unavailable: ${planModeReason}`
          }
          aria-checked={planModeEnabled}
          disabled={!planModeAvailable}
          onClick={() => {
            if (!planModeAvailable) return
            onTogglePlanMode()
          }}
          className="relative inline-flex h-5 w-[34px] items-center rounded-full transition-colors disabled:cursor-not-allowed disabled:opacity-70"
          style={{
            background: planModeEnabled ? '#3b82f6' : 'rgba(15,23,42,0.12)',
            cursor: planModeAvailable ? 'default' : 'not-allowed',
          }}
        >
          <span
            className="inline-flex h-3.5 w-3.5 rounded-full bg-white transition-transform"
            style={{
              transform: planModeEnabled ? 'translateX(17px)' : 'translateX(3px)',
            }}
          />
        </button>
      </div>

      {supportsThinking && (
        <div
          className="mt-0.5 flex items-center justify-between rounded-xl px-2.5 py-2"
          style={{ color: 'var(--text-main)' }}
        >
          <span className="inline-flex items-center gap-2.5">
            <span className="inline-flex h-4 w-4 items-center justify-center">
              <ThinkingModeIcon />
            </span>
            <span>
              <span className="block text-[13px] font-medium leading-none">Thinking Mode</span>
              <span className="block text-xs whitespace-nowrap" style={{ color: 'var(--text-muted)' }}>
                Model reasoning trace (Ollama thinking)
              </span>
            </span>
          </span>
          <button
            type="button"
            role="switch"
            aria-label="Thinking mode"
            aria-checked={thinkingEnabled}
            onClick={onToggleThinkingMode}
            className="relative inline-flex h-5 w-[34px] items-center rounded-full transition-colors"
            style={{
              background: thinkingEnabled ? '#3b82f6' : 'rgba(15,23,42,0.12)',
              cursor: 'default',
            }}
          >
            <span
              className="inline-flex h-3.5 w-3.5 rounded-full bg-white transition-transform"
              style={{
                transform: thinkingEnabled ? 'translateX(17px)' : 'translateX(3px)',
              }}
            />
          </button>
        </div>
      )}
    </div>
  )
}
