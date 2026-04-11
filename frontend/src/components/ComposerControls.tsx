import { type RefObject, useState, type CSSProperties } from 'react'
import type { GPUStatus, InferenceLatency } from '../api/system'
import type { ChatLayoutDecisions } from '../utils/chatLayout'
import GpuStatusDot from './GpuStatusDot'
import {
  ChevronDownIcon,
  PlusIcon,
  PlanModeIcon,
  ThinkingModeIcon,
  SendArrowIcon,
  StopIcon,
  type ReasoningLevel,
} from './chatComposerPrimitives'

interface ComposerControlsProps {
  layoutDecisions: ChatLayoutDecisions
  selectedModel: string
  reasoningLevel: ReasoningLevel
  supportsThinking: boolean
  thinkingEnabled: boolean
  planModeEnabled: boolean
  onPlanModeChange: (enabled: boolean) => void
  plusMenuOpen: boolean
  modelMenuOpen: boolean
  reasoningMenuOpen: boolean
  isStreaming: boolean
  attachmentUploading: boolean
  canSend: boolean
  gpuStatus: GPUStatus | null
  gpuError: string | null
  inferenceLatency: InferenceLatency | null
  plusButtonRef?: RefObject<HTMLButtonElement | null>
  onTogglePlusMenu: () => void
  onToggleModelMenu: () => void
  onToggleReasoningMenu: () => void
  onThinkingEnabledChange: (enabled: boolean) => void
  thinkingTooltipEnabled?: boolean
  onStop: () => void
  onSubmit: () => void
}

function controlPillStyle(isOpen: boolean): CSSProperties {
  return {
    color: 'var(--text-muted)',
    background: isOpen ? 'var(--composer-selected-surface)' : 'transparent',
    boxShadow: isOpen ? 'var(--composer-pill-open-shadow)' : 'none',
  }
}

export default function ComposerControls({
  layoutDecisions,
  selectedModel,
  reasoningLevel,
  supportsThinking,
  thinkingEnabled,
  planModeEnabled,
  onPlanModeChange,
  plusMenuOpen,
  modelMenuOpen,
  reasoningMenuOpen,
  isStreaming,
  attachmentUploading,
  canSend,
  gpuStatus,
  gpuError,
  inferenceLatency,
  plusButtonRef,
  onTogglePlusMenu,
  onToggleModelMenu,
  onToggleReasoningMenu,
  onThinkingEnabledChange,
  thinkingTooltipEnabled = false,
  onStop,
  onSubmit,
}: ComposerControlsProps) {
  const [hoveredCapability, setHoveredCapability] = useState<'plan' | 'thinking' | null>(null)

  return (
    <div
      data-testid="composer-control-row"
      className="ui-static flex items-center justify-between gap-1 px-0.5"
    >
      <div
        data-testid="composer-left-controls"
        className={`-ml-1 flex min-w-0 flex-1 items-center ${layoutDecisions.compactComposer ? 'gap-1 overflow-x-auto pr-1.5' : 'gap-1'}`}
        style={{
          scrollbarWidth: 'none',
          msOverflowStyle: 'none',
        }}
      >
        <button
          ref={plusButtonRef}
          type="button"
          disabled={isStreaming || attachmentUploading}
          onClick={onTogglePlusMenu}
          className={`${layoutDecisions.compactComposer ? 'h-9 w-9' : 'h-10 w-10'} flex shrink-0 items-center justify-center rounded-full transition-colors disabled:opacity-40 ${plusMenuOpen ? '' : 'hover:bg-[var(--composer-control-hover-bg)]'}`}
          style={{ border: 'none', ...controlPillStyle(plusMenuOpen), color: 'var(--composer-control-icon)' }}
          title={plusMenuOpen ? 'Close actions' : 'Open upload and planning actions'}
        >
          <PlusIcon />
        </button>

        <div
          className={`flex min-w-0 flex-1 items-center ${layoutDecisions.compactComposer ? 'gap-1' : 'gap-1.5'}`}
        >
          <button
            type="button"
            aria-label="Open model menu"
            aria-expanded={modelMenuOpen}
            title={selectedModel}
            onClick={onToggleModelMenu}
            className={`inline-flex min-w-0 shrink items-center gap-1 overflow-hidden rounded-full px-2 py-1 text-[13px] font-medium transition-all ${layoutDecisions.compactComposer ? 'max-w-[min(5.5rem,28vw)]' : 'max-w-[min(9.5rem,36vw)]'}`}
            style={controlPillStyle(modelMenuOpen)}
          >
            <span className="min-w-0 flex-1 truncate text-left">{selectedModel}</span>
            <span className="inline-flex shrink-0 items-center justify-center">
              <ChevronDownIcon />
            </span>
          </button>

          <button
            type="button"
            aria-label="Open reasoning menu"
            aria-expanded={reasoningMenuOpen}
            onClick={onToggleReasoningMenu}
            className={`inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-1 text-[13px] font-medium transition-all ${layoutDecisions.compactComposer ? 'max-w-[4.5rem]' : ''}`}
            style={controlPillStyle(reasoningMenuOpen)}
          >
            <span className="truncate">
              {reasoningLevel === 'low' ? 'Low' : reasoningLevel === 'high' ? 'High' : 'Medium'}
            </span>
            <span className="inline-flex flex-shrink-0 items-center justify-center">
              <ChevronDownIcon />
            </span>
          </button>

          {planModeEnabled && (
            <button
              type="button"
              className="relative inline-flex shrink-0 items-center gap-1 text-[13px] font-medium"
              style={{ color: 'var(--theme-accent-strong)' }}
              aria-label="Plan enabled"
              title="Planning mode is enabled."
              onClick={() => onPlanModeChange(false)}
              onMouseEnter={() => setHoveredCapability('plan')}
              onMouseLeave={() => setHoveredCapability(null)}
              onFocus={() => setHoveredCapability('plan')}
              onBlur={() => setHoveredCapability(null)}
            >
              <span className="inline-flex h-4 w-4 items-center justify-center">
                <PlanModeIcon />
              </span>
              <span>Plan</span>
              {hoveredCapability === 'plan' && (
                <span
                  role="tooltip"
                  className="pointer-events-none absolute bottom-[calc(100%+0.45rem)] left-1/2 z-20 -translate-x-1/2 whitespace-nowrap rounded-full px-2 py-1 text-[11px] font-medium shadow-[0_10px_20px_rgba(15,23,42,0.14)]"
                  style={{
                    background: 'var(--composer-menu-bg-strong)',
                    color: 'var(--text-main)',
                    border: '1px solid var(--input-border)',
                  }}
                >
                  Planning mode is enabled.
                </span>
              )}
            </button>
          )}

          {supportsThinking && thinkingEnabled && (
            <button
              type="button"
              className="relative inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-1 text-[13px] font-medium transition-all"
              style={{
                color: 'var(--theme-accent-strong)',
                background:
                  hoveredCapability === 'thinking'
                    ? 'var(--composer-selected-surface)'
                    : 'transparent',
                boxShadow:
                  hoveredCapability === 'thinking'
                    ? '0 10px 20px rgba(15,23,42,0.12)'
                    : 'none',
              }}
              aria-label="Thinking mode enabled"
              title={thinkingTooltipEnabled ? 'Thinking mode is enabled.' : undefined}
              onClick={() => onThinkingEnabledChange(false)}
              onMouseEnter={() => setHoveredCapability('thinking')}
              onMouseLeave={() => setHoveredCapability(null)}
              onFocus={() => setHoveredCapability('thinking')}
              onBlur={() => setHoveredCapability(null)}
            >
              <span className="inline-flex h-4 w-4 items-center justify-center">
                <ThinkingModeIcon />
              </span>
              <span>Thinking</span>
              {thinkingTooltipEnabled && hoveredCapability === 'thinking' && (
                <span
                  role="tooltip"
                  className="pointer-events-none absolute bottom-[calc(100%+0.45rem)] left-1/2 z-20 -translate-x-1/2 whitespace-nowrap rounded-full px-2 py-1 text-[11px] font-medium shadow-[0_10px_20px_rgba(15,23,42,0.14)]"
                  style={{
                    background: 'var(--composer-menu-bg-strong)',
                    color: 'var(--text-main)',
                    border: '1px solid var(--input-border)',
                  }}
                >
                  Thinking mode is enabled.
                </span>
              )}
            </button>
          )}
        </div>
      </div>

      <div data-testid="composer-right-controls" className="flex shrink-0 items-center gap-1">
        <GpuStatusDot
          gpuStatus={gpuStatus}
          gpuError={gpuError}
          inferenceLatency={inferenceLatency}
        />
        <button
          type="button"
          onClick={isStreaming ? onStop : onSubmit}
          disabled={!isStreaming && !canSend}
          aria-label={isStreaming ? 'Stop generating' : 'Send message'}
          className="flex h-10 w-10 items-center justify-center rounded-full transition-colors disabled:opacity-90"
          style={{
            background:
              isStreaming || canSend ? 'var(--composer-send-bg)' : 'var(--composer-send-disabled-bg)',
            color: 'var(--composer-send-fg)',
            boxShadow: 'none',
            cursor: isStreaming || canSend ? 'pointer' : 'not-allowed',
          }}
          title={isStreaming ? 'Stop generating' : 'Send message'}
        >
          {isStreaming ? <StopIcon /> : <SendArrowIcon />}
        </button>
      </div>
    </div>
  )
}
