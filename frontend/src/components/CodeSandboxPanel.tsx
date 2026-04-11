import { useEffect, useRef, type CSSProperties, type KeyboardEvent } from 'react'
import type {
  CodeSandboxExecutionMode,
  CodeSandboxExecutionResponse,
  CodeSandboxFeature,
} from '../api/types'
import { CloseIcon } from './chatComposerPrimitives'

interface CodeSandboxPanelProps {
  isOpen: boolean
  feature: CodeSandboxFeature | null
  runtimeEnabled: boolean
  runPending: boolean
  executionMode: CodeSandboxExecutionMode
  code: string
  command: string
  stdin: string
  error: string | null
  result: CodeSandboxExecutionResponse | null
  liveLogs: string[]
  streamDisconnected: boolean
  onClose: () => void
  onExecutionModeChange: (value: CodeSandboxExecutionMode) => void
  onCodeChange: (value: string) => void
  onCommandChange: (value: string) => void
  onStdinChange: (value: string) => void
  onRun: () => void
}

const panelStyle = {
  borderColor: 'var(--input-border)',
  background: 'var(--composer-menu-bg-strong)',
  backdropFilter: 'blur(18px)',
} satisfies CSSProperties

const fieldStyle = {
  borderColor: 'var(--input-border)',
  background: 'var(--composer-menu-bg)',
  color: 'var(--text-main)',
} satisfies CSSProperties

export default function CodeSandboxPanel({
  isOpen,
  feature,
  runtimeEnabled,
  runPending,
  executionMode,
  code,
  command,
  stdin,
  error,
  result,
  liveLogs,
  streamDisconnected,
  onClose,
  onExecutionModeChange,
  onCodeChange,
  onCommandChange,
  onStdinChange,
  onRun,
}: CodeSandboxPanelProps) {
  const panelRef = useRef<HTMLDivElement | null>(null)
  const codeRef = useRef<HTMLTextAreaElement | null>(null)

  useEffect(() => {
    if (!isOpen) return
    codeRef.current?.focus()
  }, [isOpen])

  if (!isOpen) return null

  const description = feature?.provider_name === 'localhost'
    ? 'Execute a short shell snippet on the local host shell. This trusted-dev fallback does not provide full sandbox isolation.'
    : 'Execute a short shell snippet in an isolated, no-network sandbox.'

  const handlePanelKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'Escape') {
      event.preventDefault()
      onClose()
      return
    }
    if (event.key !== 'Tab' || !panelRef.current) return
    const focusable = Array.from(
      panelRef.current.querySelectorAll<HTMLElement>(
        'button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
      ),
    ).filter(node => !node.hasAttribute('disabled'))
    if (focusable.length === 0) return
    const first = focusable[0]
    const last = focusable[focusable.length - 1]
    if (!first || !last) return
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault()
      last.focus()
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault()
      first.focus()
    }
  }

  return (
    <div
      ref={panelRef}
      className="absolute bottom-14 left-0 z-30 w-[min(620px,calc(100vw-3rem))] rounded-3xl border p-4 shadow-[0_12px_24px_rgba(15,23,42,0.08)]"
      style={panelStyle}
      role="dialog"
      aria-modal="true"
      aria-label="Code sandbox"
      onKeyDown={handlePanelKeyDown}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold" style={{ color: 'var(--text-main)' }}>
            Run Code
          </h3>
          <p className="mt-1 text-xs" style={{ color: 'var(--text-muted)' }}>
            {description}
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="flex h-8 w-8 items-center justify-center rounded-full transition-colors hover:bg-slate-900/[0.04]"
          style={{ color: 'var(--text-muted)' }}
          title="Close code sandbox"
          aria-label="Close code sandbox"
        >
          <CloseIcon />
        </button>
      </div>

      <div className="mt-4 grid gap-3">
        <label className="grid gap-1 text-xs font-medium" style={{ color: 'var(--text-muted)' }}>
          Execution mode
          <select
            value={executionMode}
            onChange={event => onExecutionModeChange(event.target.value as CodeSandboxExecutionMode)}
            className="rounded-2xl border px-3 py-2 text-sm"
            style={fieldStyle}
            disabled={runPending || !runtimeEnabled}
          >
            <option value="sync">Sync</option>
            <option value="async">Async</option>
          </select>
        </label>

        <label className="grid gap-1 text-xs font-medium" style={{ color: 'var(--text-muted)' }}>
          Runtime preset
          <select
            value="shell"
            disabled
            className="rounded-2xl border px-3 py-2 text-sm"
            style={fieldStyle}
          >
            <option value="shell">Shell</option>
          </select>
        </label>

        <label className="grid gap-1 text-xs font-medium" style={{ color: 'var(--text-muted)' }}>
          Command
          <input
            value={command}
            onChange={event => onCommandChange(event.target.value)}
            placeholder="Optional: sh ./script.sh or python script.py"
            className="rounded-2xl border px-3 py-2 text-sm focus:outline-none"
            style={fieldStyle}
            disabled={runPending || !runtimeEnabled}
          />
        </label>

        <label className="grid gap-1 text-xs font-medium" style={{ color: 'var(--text-muted)' }}>
          Code
          <textarea
            ref={codeRef}
            value={code}
            onChange={event => onCodeChange(event.target.value)}
            placeholder="echo 'hello from the sandbox'"
            rows={8}
            className="rounded-3xl border px-3 py-3 text-sm font-medium focus:outline-none"
            style={{
              ...fieldStyle,
              fontFamily: 'Consolas, "SFMono-Regular", Menlo, monospace',
            }}
            disabled={runPending || !runtimeEnabled}
          />
        </label>

        <label className="grid gap-1 text-xs font-medium" style={{ color: 'var(--text-muted)' }}>
          stdin
          <textarea
            value={stdin}
            onChange={event => onStdinChange(event.target.value)}
            placeholder="Optional stdin content"
            rows={3}
            className="rounded-3xl border px-3 py-3 text-sm focus:outline-none"
            style={{
              ...fieldStyle,
              fontFamily: 'Consolas, "SFMono-Regular", Menlo, monospace',
            }}
            disabled={runPending || !runtimeEnabled}
          />
        </label>

        <div className="flex items-center justify-between gap-3">
          <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
            Files written under <code>outputs/</code> are reported after execution.
          </p>
          <button
            type="button"
            onClick={onRun}
            disabled={runPending || !runtimeEnabled || (!code.trim() && !command.trim())}
            className="rounded-full px-4 py-2 text-sm font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-60"
            style={{
              background: 'var(--composer-send-bg)',
              color: 'var(--composer-send-fg)',
            }}
          >
            {runPending ? 'Running...' : 'Run'}
          </button>
        </div>

        {error && (
          <div
            role="status"
            aria-live="polite"
            className="rounded-2xl border px-3 py-2 text-sm"
            style={{
              borderColor: 'var(--composer-danger-border)',
              background: 'var(--composer-danger-bg)',
              color: 'var(--composer-danger-fg)',
            }}
          >
            {error}
          </div>
        )}

        {result && (
          <div
            className="grid gap-3 rounded-3xl border p-3"
            style={{
              borderColor: 'var(--input-border)',
              background: 'var(--composer-menu-bg)',
            }}
          >
            <div className="flex flex-wrap items-center gap-2 text-xs" style={{ color: 'var(--text-muted)' }}>
              <span>Status: {result.status}</span>
              <span>Mode: {result.execution_mode}</span>
              <span>Exit: {result.exit_code ?? 'n/a'}</span>
              <span>Timed out: {result.timed_out ? 'yes' : 'no'}</span>
            </div>
            {result.execution_mode === 'async' && (
              <div className="grid gap-1">
                <span className="text-xs font-medium" style={{ color: 'var(--text-muted)' }}>
                  Live logs
                </span>
                <pre
                  className="min-h-[96px] overflow-x-auto rounded-2xl border px-3 py-2 text-xs"
                  style={{
                    ...fieldStyle,
                    fontFamily: 'Consolas, "SFMono-Regular", Menlo, monospace',
                  }}
                >
                  {liveLogs.length > 0 ? liveLogs.join('') : '(waiting for logs)'}
                </pre>
                {streamDisconnected && result.status !== 'completed' && result.status !== 'failed' && (
                  <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                    Live stream disconnected. Polling durable execution status.
                  </p>
                )}
              </div>
            )}
            <div className="grid gap-2 md:grid-cols-2">
              <div className="grid gap-1">
                <span className="text-xs font-medium" style={{ color: 'var(--text-muted)' }}>
                  stdout
                </span>
                <pre
                  className="min-h-[96px] overflow-x-auto rounded-2xl border px-3 py-2 text-xs"
                  style={{
                    ...fieldStyle,
                    fontFamily: 'Consolas, "SFMono-Regular", Menlo, monospace',
                  }}
                >
                  {result.stdout || '(empty)'}
                </pre>
              </div>
              <div className="grid gap-1">
                <span className="text-xs font-medium" style={{ color: 'var(--text-muted)' }}>
                  stderr
                </span>
                <pre
                  className="min-h-[96px] overflow-x-auto rounded-2xl border px-3 py-2 text-xs"
                  style={{
                    ...fieldStyle,
                    fontFamily: 'Consolas, "SFMono-Regular", Menlo, monospace',
                  }}
                >
                  {result.stderr || '(empty)'}
                </pre>
              </div>
            </div>
            {result.output_files.length > 0 && (
              <div className="grid gap-1">
                <span className="text-xs font-medium" style={{ color: 'var(--text-muted)' }}>
                  Output files
                </span>
                <ul className="grid gap-1 text-xs" style={{ color: 'var(--text-main)' }}>
                  {result.output_files.map(file => (
                    <li key={file.path}>
                      {file.path} ({file.byte_size} B)
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
