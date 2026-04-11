import { type CSSProperties } from 'react'
import type { CodeSandboxExecutionResponse } from '../api/types'
import { CloseIcon } from './chatComposerPrimitives'

interface CodeSandboxPanelProps {
  isOpen: boolean
  runtimeEnabled: boolean
  runPending: boolean
  code: string
  command: string
  stdin: string
  error: string | null
  result: CodeSandboxExecutionResponse | null
  onClose: () => void
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
  runtimeEnabled,
  runPending,
  code,
  command,
  stdin,
  error,
  result,
  onClose,
  onCodeChange,
  onCommandChange,
  onStdinChange,
  onRun,
}: CodeSandboxPanelProps) {
  if (!isOpen) return null

  return (
    <div
      className="absolute bottom-14 left-0 z-30 w-[min(620px,calc(100vw-3rem))] rounded-3xl border p-4 shadow-[0_12px_24px_rgba(15,23,42,0.08)]"
      style={panelStyle}
      role="dialog"
      aria-label="Code sandbox"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold" style={{ color: 'var(--text-main)' }}>
            Run Code
          </h3>
          <p className="mt-1 text-xs" style={{ color: 'var(--text-muted)' }}>
            Execute a short shell snippet in an isolated, no-network sandbox.
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="flex h-8 w-8 items-center justify-center rounded-full transition-colors hover:bg-slate-900/[0.04]"
          style={{ color: 'var(--text-muted)' }}
          title="Close code sandbox"
        >
          <CloseIcon />
        </button>
      </div>

      <div className="mt-4 grid gap-3">
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
              <span>Exit: {result.exit_code ?? 'n/a'}</span>
              <span>Timed out: {result.timed_out ? 'yes' : 'no'}</span>
            </div>
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
