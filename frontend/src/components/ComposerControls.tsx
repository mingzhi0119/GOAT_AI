import { useState, type CSSProperties } from 'react'
import type { GPUStatus, InferenceLatency } from '../api/system'
import type { ChatLayoutDecisions } from '../utils/chatLayout'
import GpuStatusDot from './GpuStatusDot'
import {
  ChevronDownIcon,
  PlusIcon,
  PlanModeIcon,
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
  onTogglePlusMenu: () => void
  onToggleModelMenu: () => void
  onToggleReasoningMenu: () => void
  onToggleThinkingMode: () => void
  onStop: () => void
  onSubmit: () => void
}

function controlPillStyle(isOpen: boolean): CSSProperties {
  return {
    color: 'var(--text-muted)',
    background: isOpen ? 'rgba(17,24,39,0.08)' : 'transparent',
    boxShadow: isOpen ? '0 6px 14px rgba(15,23,42,0.08)' : 'none',
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
  onTogglePlusMenu,
  onToggleModelMenu,
  onToggleReasoningMenu,
  onToggleThinkingMode,
  onStop,
  onSubmit,
}: ComposerControlsProps) {
  const [hoveredIndicator, setHoveredIndicator] = useState<boolean>(false)

  return (
    <div
      data-testid="composer-control-row"
      className="ui-static flex items-center justify-between gap-2 px-0.5"
    >
      <div
        data-testid="composer-left-controls"
        className={`-ml-1 flex min-w-0 flex-1 items-center ${layoutDecisions.compactComposer ? 'gap-1.5 overflow-x-auto pr-2' : 'gap-1.5'}`}
        style={{
          scrollbarWidth: 'none',
          msOverflowStyle: 'none',
        }}
      >
        <button
          type="button"
          disabled={isStreaming || attachmentUploading}
          onClick={onTogglePlusMenu}
          className={`${layoutDecisions.compactComposer ? 'h-9 w-9' : 'h-10 w-10'} flex flex-shrink-0 items-center justify-center rounded-full transition-all disabled:opacity-40`}
          style={{ border: 'none', ...controlPillStyle(plusMenuOpen), color: 'rgba(17,24,39,0.42)' }}
          title={plusMenuOpen ? 'Close actions' : 'Open upload and planning actions'}
          onMouseEnter={e => {
            if (!plusMenuOpen) e.currentTarget.style.background = 'rgba(17,24,39,0.08)'
          }}
          onMouseLeave={e => {
            if (!plusMenuOpen) e.currentTarget.style.background = 'transparent'
          }}
        >
          <PlusIcon />
        </button>

        <div className={`flex min-w-0 flex-shrink-0 items-center ${layoutDecisions.compactComposer ? 'gap-1.5' : 'gap-3'}`}>
          <button
            type="button"
            aria-label="Open model menu"
            aria-expanded={modelMenuOpen}
            onClick={onToggleModelMenu}
            className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1.5 text-[13px] font-medium transition-all ${layoutDecisions.compactComposer ? 'max-w-[104px]' : 'max-w-[180px]'}`}
            style={controlPillStyle(modelMenuOpen)}
          >
            <span className="truncate">{selectedModel}</span>
            <span className="inline-flex flex-shrink-0 items-center justify-center">
              <ChevronDownIcon />
            </span>
          </button>

          <button
            type="button"
            aria-label="Open reasoning menu"
            aria-expanded={reasoningMenuOpen}
            onClick={onToggleReasoningMenu}
            className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1.5 text-[13px] font-medium transition-all ${layoutDecisions.compactComposer ? 'max-w-[78px] flex-shrink-0' : ''}`}
            style={controlPillStyle(reasoningMenuOpen)}
          >
            <span className="truncate">
              {reasoningLevel === 'low' ? 'Low' : reasoningLevel === 'high' ? 'High' : 'Medium'}
            </span>
            <span className="inline-flex flex-shrink-0 items-center justify-center">
              <ChevronDownIcon />
            </span>
          </button>

          {supportsThinking && (
            <button
              type="button"
              aria-label={thinkingEnabled ? 'Set quick mode' : 'Set thinking mode'}
              aria-pressed={thinkingEnabled}
              onClick={onToggleThinkingMode}
              className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1.5 text-[13px] font-medium transition-colors hover:bg-slate-900/[0.06] ${layoutDecisions.compactComposer ? 'max-w-[104px] flex-shrink-0' : ''}`}
              style={{
                color: 'var(--text-muted)',
                background: 'transparent',
                borderColor: 'var(--border-color)',
              }}
              title={thinkingEnabled ? 'Thinking enabled' : 'Quick mode enabled'}
            >
              <span className="truncate">{thinkingEnabled ? 'Thinking' : 'Quick'}</span>
            </button>
          )}

          {planModeEnabled && (
            <button
              type="button"
              className="relative inline-flex items-center gap-1.5 text-[13px] font-medium"
              style={{ color: '#3b82f6' }}
              aria-label="Plan enabled"
              title="Planning mode is enabled."
              onClick={() => onPlanModeChange(false)}
              onMouseEnter={() => setHoveredIndicator(true)}
              onMouseLeave={() => setHoveredIndicator(false)}
              onFocus={() => setHoveredIndicator(true)}
              onBlur={() => setHoveredIndicator(false)}
            >
              <span className="inline-flex h-4 w-4 items-center justify-center">
                <PlanModeIcon />
              </span>
              <span>Plan</span>
              {hoveredIndicator && (
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
        </div>
      </div>

      <div data-testid="composer-right-controls" className="flex flex-shrink-0 items-center gap-2">
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
          className="flex h-10 w-10 items-center justify-center rounded-full transition-all"
          style={{
            background: isStreaming ? '#111111' : canSend ? '#111111' : '#9ca3af',
            color: '#ffffff',
            boxShadow: canSend || isStreaming ? 'none' : 'inset 0 0 0 1px rgba(0,0,0,0.04)',
            cursor: 'default',
          }}
          title={isStreaming ? 'Stop generating' : 'Send message'}
        >
          {isStreaming ? <StopIcon /> : <SendArrowIcon />}
        </button>
      </div>
    </div>
  )
}
