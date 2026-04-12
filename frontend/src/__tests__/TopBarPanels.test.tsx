import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { createRef } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { ConversationActionsMenu, SettingsPanel } from '../components/TopBarPanels'

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

  it('keeps settings callbacks wired through the extracted panel', () => {
    const onApiKeyChange = vi.fn()
    const onOwnerIdChange = vi.fn()
    const onSystemInstructionChange = vi.fn()
    const onAdvancedOpenChange = vi.fn()
    const onTemperatureChange = vi.fn()
    const onMaxTokensChange = vi.fn()
    const onTopPChange = vi.fn()
    const onResetAdvanced = vi.fn()
    const onOpenAppearance = vi.fn()
    const onClose = vi.fn()

    render(
      <SettingsPanel
        panelId="settings-panel"
        triggerId="settings-trigger"
        appearanceSummary="Classic System"
        advancedOpen={true}
        apiKey="secret-123"
        ownerId="alice"
        systemInstruction="Be clear."
        temperature={0.7}
        maxTokens={1024}
        topP={0.9}
        onApiKeyChange={onApiKeyChange}
        onOwnerIdChange={onOwnerIdChange}
        onSystemInstructionChange={onSystemInstructionChange}
        onAdvancedOpenChange={onAdvancedOpenChange}
        onTemperatureChange={onTemperatureChange}
        onMaxTokensChange={onMaxTokensChange}
        onTopPChange={onTopPChange}
        onResetAdvanced={onResetAdvanced}
        onOpenAppearance={onOpenAppearance}
        onClose={onClose}
      />,
    )

    fireEvent.change(screen.getByPlaceholderText(/optional: tone/i), {
      target: { value: 'Use bullets.' },
    })
    fireEvent.change(screen.getByLabelText('API key'), {
      target: { value: 'next-key' },
    })
    fireEvent.change(screen.getByLabelText('Owner ID'), {
      target: { value: 'owner-42' },
    })

    const inputs = screen.getAllByRole('spinbutton')
    fireEvent.change(inputs[0]!, { target: { value: '1.1' } })
    fireEvent.change(inputs[1]!, { target: { value: '999999' } })
    fireEvent.change(inputs[2]!, { target: { value: '0.8' } })
    fireEvent.click(screen.getByRole('button', { name: /reset generation settings to defaults/i }))
    fireEvent.click(screen.getByText('Classic System').closest('button') as HTMLButtonElement)

    expect(onSystemInstructionChange).toHaveBeenCalledWith('Use bullets.')
    expect(onApiKeyChange).toHaveBeenCalledWith('next-key')
    expect(onOwnerIdChange).toHaveBeenCalledWith('owner-42')
    expect(onTemperatureChange).toHaveBeenCalledWith(1.1)
    expect(onMaxTokensChange).toHaveBeenCalledWith(131072)
    expect(onTopPChange).toHaveBeenCalledWith(0.8)
    expect(onResetAdvanced).toHaveBeenCalled()
    expect(onAdvancedOpenChange).toHaveBeenCalledWith(true)
    expect(onOpenAppearance).toHaveBeenCalled()
    expect(onClose).toHaveBeenCalled()
  })

  it('renders desktop diagnostics details when available', () => {
    render(
      <SettingsPanel
        panelId="settings-panel"
        triggerId="settings-trigger"
        appearanceSummary="Classic System"
        advancedOpen={false}
        desktopDiagnostics={{
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
        }}
        apiKey=""
        ownerId=""
        systemInstruction=""
        temperature={0.7}
        maxTokens={1024}
        topP={0.9}
        onApiKeyChange={vi.fn()}
        onOwnerIdChange={vi.fn()}
        onSystemInstructionChange={vi.fn()}
        onAdvancedOpenChange={vi.fn()}
        onTemperatureChange={vi.fn()}
        onMaxTokensChange={vi.fn()}
        onTopPChange={vi.fn()}
        onResetAdvanced={vi.fn()}
        onOpenAppearance={vi.fn()}
        onClose={vi.fn()}
      />,
    )

    expect(screen.getByText('Desktop runtime')).toBeInTheDocument()
    expect(screen.getByText('http://127.0.0.1:62606')).toBeInTheDocument()
    expect(screen.getByText(/failing: ollama/i)).toBeInTheDocument()
    expect(screen.getByText('C:/GOAT/Desktop/logs/desktop-shell.log')).toBeInTheDocument()
  })

  it('supports Escape close and focus cycling inside settings', async () => {
    const onClose = vi.fn()

    render(
      <SettingsPanel
        panelId="settings-panel"
        triggerId="settings-trigger"
        appearanceSummary="Classic System"
        advancedOpen={false}
        apiKey=""
        ownerId=""
        systemInstruction=""
        temperature={0.7}
        maxTokens={1024}
        topP={0.9}
        onApiKeyChange={vi.fn()}
        onOwnerIdChange={vi.fn()}
        onSystemInstructionChange={vi.fn()}
        onAdvancedOpenChange={vi.fn()}
        onTemperatureChange={vi.fn()}
        onMaxTokensChange={vi.fn()}
        onTopPChange={vi.fn()}
        onResetAdvanced={vi.fn()}
        onOpenAppearance={vi.fn()}
        onClose={onClose}
      />,
    )

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
