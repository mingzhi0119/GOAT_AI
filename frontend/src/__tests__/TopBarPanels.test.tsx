import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { createRef } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { ConversationActionsMenu, SettingsPanel } from '../components/TopBarPanels'

function renderSettingsPanel(overrides: Partial<Parameters<typeof SettingsPanel>[0]> = {}) {
  return render(
    <SettingsPanel
      panelId="settings-panel"
      triggerId="settings-trigger"
      appearanceSummary="Classic System"
      advancedOpen={true}
      systemInstruction="Be clear."
      temperature={0.7}
      maxTokens={1024}
      topP={0.9}
      onSystemInstructionChange={vi.fn()}
      onAdvancedOpenChange={vi.fn()}
      onTemperatureChange={vi.fn()}
      onMaxTokensChange={vi.fn()}
      onTopPChange={vi.fn()}
      onResetAdvanced={vi.fn()}
      onOpenAppearance={vi.fn()}
      onClose={vi.fn()}
      {...overrides}
    />,
  )
}

describe('TopBarPanels', () => {
  it('disables rename and delete when there is no saved session', async () => {
    const triggerRef = createRef<HTMLButtonElement>()
    render(
      <>
        <button ref={triggerRef} id="conversation-actions-trigger" type="button">
          Actions
        </button>
        <ConversationActionsMenu
          menuId="conversation-actions-menu"
          triggerId="conversation-actions-trigger"
          triggerRef={triggerRef}
          focusStrategy="first"
          hasSession={false}
          onRenameConversation={vi.fn()}
          onExportMarkdown={vi.fn()}
          onDeleteConversation={vi.fn()}
          onClose={vi.fn()}
          isNarrow={false}
        />
      </>,
    )

    await waitFor(() => {
      expect(screen.getByRole('menuitem', { name: /export to markdown/i })).toHaveFocus()
    })
    expect(screen.getByRole('menuitem', { name: /rename/i })).toBeDisabled()
    expect(screen.getByRole('menuitem', { name: /delete/i })).toBeDisabled()
    expect(screen.getByRole('menuitem', { name: /export to markdown/i })).toBeEnabled()
  })

  it('keeps settings callbacks wired through the extracted panel without auth controls', () => {
    const onSystemInstructionChange = vi.fn()
    const onAdvancedOpenChange = vi.fn()
    const onTemperatureChange = vi.fn()
    const onMaxTokensChange = vi.fn()
    const onTopPChange = vi.fn()
    const onResetAdvanced = vi.fn()
    const onOpenAppearance = vi.fn()
    const onClose = vi.fn()

    renderSettingsPanel({
      onSystemInstructionChange,
      onAdvancedOpenChange,
      onTemperatureChange,
      onMaxTokensChange,
      onTopPChange,
      onResetAdvanced,
      onOpenAppearance,
      onClose,
    })

    fireEvent.change(screen.getByPlaceholderText(/optional: tone/i), {
      target: { value: 'Use bullets.' },
    })
    expect(screen.queryByLabelText('API key')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Owner ID')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /logout/i })).not.toBeInTheDocument()

    const inputs = screen.getAllByRole('spinbutton')
    fireEvent.change(inputs[0]!, { target: { value: '1.1' } })
    fireEvent.change(inputs[1]!, { target: { value: '999999' } })
    fireEvent.change(inputs[2]!, { target: { value: '0.8' } })
    fireEvent.click(screen.getByRole('button', { name: /reset generation settings to defaults/i }))
    fireEvent.click(screen.getByText('Classic System').closest('button') as HTMLButtonElement)

    expect(onSystemInstructionChange).toHaveBeenCalledWith('Use bullets.')
    expect(onTemperatureChange).toHaveBeenCalledWith(1.1)
    expect(onMaxTokensChange).toHaveBeenCalledWith(131072)
    expect(onTopPChange).toHaveBeenCalledWith(0.8)
    expect(onResetAdvanced).toHaveBeenCalled()
    expect(onAdvancedOpenChange).toHaveBeenCalledWith(true)
    expect(onOpenAppearance).toHaveBeenCalled()
    expect(onClose).toHaveBeenCalled()
  })

  it('renders desktop diagnostics details when available', () => {
    renderSettingsPanel({
      advancedOpen: false,
      desktopDiagnostics: {
        desktop_mode: true,
        backend_base_url: 'http://127.0.0.1:62606',
        readiness_ok: false,
        failing_checks: ['ollama'],
        skipped_checks: [],
        code_sandbox_effective_enabled: true,
        workbench_effective_enabled: false,
        app_data_dir: 'C:/GOAT/Desktop',
        runtime_root: 'C:/GOAT/Desktop',
        data_dir: 'C:/GOAT/Desktop/data',
        log_dir: 'C:/GOAT/Desktop/logs',
        log_db_path: 'C:/GOAT/Desktop/chat_logs.db',
        packaged_shell_log_path: 'C:/GOAT/Desktop/logs/desktop-shell.log',
      },
    })

    expect(screen.getByText('Desktop runtime')).toBeInTheDocument()
    expect(screen.getByText('http://127.0.0.1:62606')).toBeInTheDocument()
    expect(screen.getByText(/failing: ollama/i)).toBeInTheDocument()
    expect(screen.getByText('C:/GOAT/Desktop/logs/desktop-shell.log')).toBeInTheDocument()
  })

  it('keeps desktop diagnostics read-only when packaged runtime is absent', () => {
    renderSettingsPanel({
      advancedOpen: false,
      desktopDiagnostics: {
        desktop_mode: false,
        backend_base_url: null,
        readiness_ok: null,
        failing_checks: [],
        skipped_checks: [],
        code_sandbox_effective_enabled: null,
        workbench_effective_enabled: null,
        app_data_dir: null,
        runtime_root: null,
        data_dir: null,
        log_dir: null,
        log_db_path: null,
        packaged_shell_log_path: null,
      },
    })

    expect(screen.getByText(/read-only diagnostics/i)).toBeInTheDocument()
    expect(screen.getByText('Desktop runtime not detected in this deployment.')).toBeInTheDocument()
    expect(screen.queryByText('Summary')).not.toBeInTheDocument()
    expect(screen.queryByText(/Workbench on/i)).not.toBeInTheDocument()
  })

  it('supports Escape close and focus cycling inside settings', async () => {
    const onClose = vi.fn()

    renderSettingsPanel({
      advancedOpen: false,
      systemInstruction: '',
      onClose,
    })

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /close settings/i })).toHaveFocus()
    })

    fireEvent.keyDown(screen.getByRole('dialog', { name: /settings/i }), {
      key: 'Tab',
      shiftKey: true,
    })
    expect(screen.getByText('Classic System').closest('button')).toHaveFocus()

    fireEvent.keyDown(screen.getByRole('dialog', { name: /settings/i }), { key: 'Escape' })
    expect(onClose).toHaveBeenCalled()
  })
})
