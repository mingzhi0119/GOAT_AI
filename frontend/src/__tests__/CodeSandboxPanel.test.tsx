import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import CodeSandboxPanel from '../components/CodeSandboxPanel'
import type { CodeSandboxExecutionResponse } from '../api/types'

const baseResult: CodeSandboxExecutionResponse = {
  execution_id: 'cs-1',
  status: 'running',
  execution_mode: 'async',
  runtime_preset: 'shell',
  network_policy: 'disabled',
  created_at: '2026-04-10T00:00:00Z',
  updated_at: '2026-04-10T00:00:01Z',
  started_at: '2026-04-10T00:00:00Z',
  finished_at: null,
  provider_name: 'docker',
  isolation_level: 'container',
  network_policy_enforced: true,
  exit_code: null,
  stdout: '',
  stderr: '',
  timed_out: false,
  error_detail: null,
  output_files: [{ path: 'report.txt', byte_size: 12 }],
}

describe('CodeSandboxPanel', () => {
  it('focuses the code area on open and traps tab navigation', () => {
    render(
      <CodeSandboxPanel
        isOpen={true}
        feature={null}
        runtimeEnabled={true}
        runPending={false}
        executionMode="sync"
        code="echo ok"
        command=""
        stdin=""
        error={null}
        result={null}
        liveLogs={[]}
        streamDisconnected={false}
        onClose={vi.fn()}
        onExecutionModeChange={vi.fn()}
        onCodeChange={vi.fn()}
        onCommandChange={vi.fn()}
        onStdinChange={vi.fn()}
        onRun={vi.fn()}
      />,
    )

    const dialog = screen.getByRole('dialog', { name: /code sandbox/i })
    const closeButton = screen.getByRole('button', { name: /close code sandbox/i })
    const runButton = screen.getByRole('button', { name: 'Run' })
    const codeArea = screen.getByPlaceholderText("echo 'hello from the sandbox'")

    expect(document.activeElement).toBe(codeArea)

    runButton.focus()
    fireEvent.keyDown(dialog, { key: 'Tab' })
    expect(document.activeElement).toBe(closeButton)

    closeButton.focus()
    fireEvent.keyDown(dialog, { key: 'Tab', shiftKey: true })
    expect(document.activeElement).toBe(runButton)
  })

  it('renders async results, live logs, output files, and localhost description', () => {
    render(
      <CodeSandboxPanel
        isOpen={true}
        feature={{
          policy_allowed: true,
          allowed_by_config: true,
          available_on_host: true,
          effective_enabled: true,
          provider_name: 'localhost',
          isolation_level: 'host',
          network_policy_enforced: false,
          deny_reason: null,
        }}
        runtimeEnabled={true}
        runPending={false}
        executionMode="async"
        code="echo ok"
        command=""
        stdin=""
        error={null}
        result={baseResult}
        liveLogs={['hello\n']}
        streamDisconnected={true}
        onClose={vi.fn()}
        onExecutionModeChange={vi.fn()}
        onCodeChange={vi.fn()}
        onCommandChange={vi.fn()}
        onStdinChange={vi.fn()}
        onRun={vi.fn()}
      />,
    )

    expect(screen.getByText(/trusted-dev fallback/i)).toBeInTheDocument()
    expect(screen.getByText('hello')).toBeInTheDocument()
    expect(screen.getByText(/Live stream disconnected/i)).toBeInTheDocument()
    expect(screen.getByText(/report.txt \(12 B\)/i)).toBeInTheDocument()
  })

  it('keeps form inputs editable even when runtime execution is unavailable', () => {
    const onCommandChange = vi.fn()
    const onCodeChange = vi.fn()
    const onStdinChange = vi.fn()

    render(
      <CodeSandboxPanel
        isOpen={true}
        feature={{
          policy_allowed: true,
          allowed_by_config: true,
          available_on_host: false,
          effective_enabled: false,
          provider_name: 'docker',
          isolation_level: 'container',
          network_policy_enforced: true,
          deny_reason: 'docker_unavailable',
        }}
        runtimeEnabled={false}
        runPending={false}
        executionMode="sync"
        code=""
        command=""
        stdin=""
        error={null}
        result={null}
        liveLogs={[]}
        streamDisconnected={false}
        onClose={vi.fn()}
        onExecutionModeChange={vi.fn()}
        onCodeChange={onCodeChange}
        onCommandChange={onCommandChange}
        onStdinChange={onStdinChange}
        onRun={vi.fn()}
      />,
    )

    const commandInput = screen.getByPlaceholderText(/optional: sh/i)
    const codeArea = screen.getByPlaceholderText("echo 'hello from the sandbox'")
    const stdinArea = screen.getByPlaceholderText(/optional stdin content/i)

    expect(commandInput).toBeEnabled()
    expect(codeArea).toBeEnabled()
    expect(stdinArea).toBeEnabled()
    expect(screen.getByRole('button', { name: 'Run' })).toBeDisabled()

    fireEvent.change(commandInput, { target: { value: 'python app.py' } })
    fireEvent.change(codeArea, { target: { value: 'print(1)' } })
    fireEvent.change(stdinArea, { target: { value: 'payload' } })

    expect(onCommandChange).toHaveBeenCalledWith('python app.py')
    expect(onCodeChange).toHaveBeenCalledWith('print(1)')
    expect(onStdinChange).toHaveBeenCalledWith('payload')
  })
})
