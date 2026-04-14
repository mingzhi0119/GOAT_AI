import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import TopBar from '../components/TopBar'

function buildSharedAccessProps() {
  return {
    sharedAccessSession: null,
    isSigningOut: false,
    onLogout: vi.fn(),
  }
}

function renderTopBar() {
  const onOpenAppearance = vi.fn()
  const onRenameConversation = vi.fn()
  const onSystemInstructionChange = vi.fn()
  const onExportMarkdown = vi.fn()
  const onDeleteConversation = vi.fn()
  const onAdvancedOpenChange = vi.fn()
  const onTemperatureChange = vi.fn()
  const onMaxTokensChange = vi.fn()
  const onTopPChange = vi.fn()
  const onResetAdvanced = vi.fn()

  const view = render(
    <TopBar
      sessionTitle="Strategy Sync"
      hasSession={true}
      modelCapabilities={['completion', 'tools', 'thinking', 'vision']}
      appearanceSummary="Classic System"
      desktopDiagnostics={null}
      desktopDiagnosticsError={null}
      onOpenAppearance={onOpenAppearance}
      onRenameConversation={onRenameConversation}
      thinkingEnabled={true}
      apiKey="secret-123"
      ownerId="alice"
      onApiKeyChange={vi.fn()}
      onOwnerIdChange={vi.fn()}
      systemInstruction="Be concise."
      onSystemInstructionChange={onSystemInstructionChange}
      onExportMarkdown={onExportMarkdown}
      onDeleteConversation={onDeleteConversation}
      advancedOpen={true}
      onAdvancedOpenChange={onAdvancedOpenChange}
      temperature={0.7}
      onTemperatureChange={onTemperatureChange}
      maxTokens={4096}
      onMaxTokensChange={onMaxTokensChange}
      topP={0.9}
      onTopPChange={onTopPChange}
      onResetAdvanced={onResetAdvanced}
      {...buildSharedAccessProps()}
    />,
  )

  return {
    ...view,
    onSystemInstructionChange,
    onExportMarkdown,
    onDeleteConversation,
    onAdvancedOpenChange,
    onTemperatureChange,
    onMaxTokensChange,
    onTopPChange,
    onResetAdvanced,
    onOpenAppearance,
    onRenameConversation,
  }
}

describe('TopBar options callout', () => {
  it('shows the session title on the left and model skills beside it', () => {
    renderTopBar()

    expect(screen.getByRole('heading', { name: 'Strategy Sync' })).toHaveStyle({
      color: 'var(--text-main)',
    })
    expect(screen.queryByText('Skills')).not.toBeInTheDocument()
    const badges = screen.getAllByTestId('model-capability-badge')
    expect(badges.map(node => node.textContent)).toEqual(['Thinking', 'Vision', 'Tools'])
    expect(screen.getByText('Thinking')).toHaveStyle({
      color: 'var(--theme-accent-contrast)',
    })
    expect(screen.getByText('Vision')).toBeInTheDocument()
  })

  it('opens the settings callout and no longer shows legacy helper copy', () => {
    renderTopBar()

    fireEvent.click(screen.getByRole('button', { name: /settings/i }))

    expect(screen.getByRole('dialog', { name: /settings/i })).toBeInTheDocument()
    expect(screen.queryByText(/Enter sends the message/i)).not.toBeInTheDocument()
    expect(screen.getByText(/^Generation$/)).toBeInTheDocument()
    expect(screen.getByLabelText('API key')).toHaveValue('secret-123')
    expect(screen.getByLabelText('Owner ID')).toHaveValue('alice')
  })

  it('removes the max-token helper copy from the options panel', () => {
    renderTopBar()
    fireEvent.click(screen.getByRole('button', { name: /settings/i }))
    expect(screen.queryByText(/API allows up to 131,072 generation tokens/i)).not.toBeInTheDocument()
  })

  it('keeps system instruction editing and clear actions wired', () => {
    const { onSystemInstructionChange } = renderTopBar()

    fireEvent.click(screen.getByRole('button', { name: /settings/i }))
    fireEvent.change(screen.getByPlaceholderText(/optional: tone, format, or constraints/i), {
      target: { value: 'Use bullets.' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Clear' }))

    expect(onSystemInstructionChange).toHaveBeenCalledWith('Use bullets.')
    expect(onSystemInstructionChange).toHaveBeenCalledWith('')
  })

  it('keeps protected-access settings wired', () => {
    const onApiKeyChange = vi.fn()
    const onOwnerIdChange = vi.fn()

    render(
      <TopBar
        sessionTitle="Strategy Sync"
        hasSession={true}
        modelCapabilities={['completion', 'tools']}
        appearanceSummary="Classic System"
        desktopDiagnostics={null}
        desktopDiagnosticsError={null}
        onOpenAppearance={vi.fn()}
        onRenameConversation={vi.fn()}
        thinkingEnabled={false}
        apiKey=""
        ownerId=""
        onApiKeyChange={onApiKeyChange}
        onOwnerIdChange={onOwnerIdChange}
        systemInstruction=""
        onSystemInstructionChange={vi.fn()}
        onExportMarkdown={vi.fn()}
        onDeleteConversation={vi.fn()}
        advancedOpen={true}
        onAdvancedOpenChange={vi.fn()}
        temperature={0.7}
        onTemperatureChange={vi.fn()}
        maxTokens={4096}
        onMaxTokensChange={vi.fn()}
        topP={0.9}
        onTopPChange={vi.fn()}
        onResetAdvanced={vi.fn()}
        {...buildSharedAccessProps()}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: /settings/i }))
    fireEvent.change(screen.getByLabelText('API key'), { target: { value: 'next-key' } })
    fireEvent.change(screen.getByLabelText('Owner ID'), { target: { value: 'owner-42' } })

    expect(onApiKeyChange).toHaveBeenCalledWith('next-key')
    expect(onOwnerIdChange).toHaveBeenCalledWith('owner-42')
  })

  it('keeps generation settings, appearance, rename, export, and delete actions wired', () => {
    const {
      onTemperatureChange,
      onMaxTokensChange,
      onTopPChange,
      onResetAdvanced,
      onRenameConversation,
      onExportMarkdown,
      onDeleteConversation,
      onOpenAppearance,
    } = renderTopBar()

    fireEvent.click(screen.getByRole('button', { name: /settings/i }))

    const inputs = screen.getAllByRole('spinbutton')
    fireEvent.change(inputs[0]!, { target: { value: '1.1' } })
    fireEvent.change(inputs[1]!, { target: { value: '999999' } })
    fireEvent.change(inputs[2]!, { target: { value: '0.8' } })
    fireEvent.click(screen.getByRole('button', { name: /reset generation settings to defaults/i }))
    fireEvent.click(screen.getByText('Classic System').closest('button') as HTMLButtonElement)
    fireEvent.click(screen.getByRole('button', { name: /conversation actions/i }))
    fireEvent.click(screen.getByRole('menuitem', { name: /rename/i }))
    fireEvent.click(screen.getByRole('button', { name: /conversation actions/i }))
    fireEvent.click(screen.getByRole('menuitem', { name: /export to markdown/i }))
    fireEvent.click(screen.getByRole('button', { name: /conversation actions/i }))
    fireEvent.click(screen.getByRole('menuitem', { name: /delete/i }))

    expect(onTemperatureChange).toHaveBeenCalledWith(1.1)
    expect(onMaxTokensChange).toHaveBeenCalledWith(131072)
    expect(onTopPChange).toHaveBeenCalledWith(0.8)
    expect(onResetAdvanced).toHaveBeenCalled()
    expect(onRenameConversation).toHaveBeenCalled()
    expect(onExportMarkdown).toHaveBeenCalled()
    expect(onDeleteConversation).toHaveBeenCalled()
    expect(onOpenAppearance).toHaveBeenCalled()
  })

  it('keeps export, rename, and delete in the ellipsis menu', () => {
    renderTopBar()

    fireEvent.click(screen.getByRole('button', { name: /settings/i }))
    fireEvent.click(screen.getByRole('button', { name: /conversation actions/i }))
    expect(screen.getByRole('menu', { name: /conversation actions/i })).toBeInTheDocument()
    expect(screen.getByRole('menuitem', { name: /rename/i })).toBeInTheDocument()
    expect(screen.getByRole('menuitem', { name: /export to markdown/i })).toBeInTheDocument()
    expect(screen.getByRole('menuitem', { name: /delete/i })).toBeInTheDocument()
  })

  it('supports keyboard navigation and Escape focus return for conversation actions', async () => {
    renderTopBar()

    const trigger = screen.getByRole('button', { name: /conversation actions/i })
    trigger.focus()
    fireEvent.keyDown(trigger, { key: 'ArrowDown' })

    await waitFor(() => {
      expect(screen.getByRole('menuitem', { name: /rename/i })).toHaveFocus()
    })

    fireEvent.keyDown(screen.getByRole('menu', { name: /conversation actions/i }), {
      key: 'ArrowDown',
    })
    expect(screen.getByRole('menuitem', { name: /export to markdown/i })).toHaveFocus()

    fireEvent.keyDown(screen.getByRole('menu', { name: /conversation actions/i }), {
      key: 'End',
    })
    expect(screen.getByRole('menuitem', { name: /delete/i })).toHaveFocus()

    fireEvent.keyDown(screen.getByRole('menu', { name: /conversation actions/i }), {
      key: 'Escape',
    })

    await waitFor(() => {
      expect(trigger).toHaveFocus()
    })
  })

  it('traps focus inside settings and restores focus when it closes', async () => {
    renderTopBar()

    const settingsTrigger = screen.getByRole('button', { name: /settings/i })
    fireEvent.click(settingsTrigger)

    const dialog = screen.getByRole('dialog', { name: /settings/i })
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /close settings/i })).toHaveFocus()
    })

    fireEvent.keyDown(dialog, { key: 'Tab', shiftKey: true })
    await waitFor(() => {
      expect(screen.getByText('Classic System').closest('button')).toHaveFocus()
    })

    fireEvent.keyDown(dialog, { key: 'Escape' })
    await waitFor(() => {
      expect(settingsTrigger).toHaveFocus()
    })
  })

  it('shows only two capability badges in narrow mode and summarizes the rest without a hover tooltip', () => {
    render(
      <TopBar
        sessionTitle="Strategy Sync"
        hasSession={true}
        modelCapabilities={['completion', 'tools', 'thinking', 'vision']}
        appearanceSummary="Classic System"
        layoutMode="narrow"
        desktopDiagnostics={null}
        desktopDiagnosticsError={null}
        onOpenAppearance={vi.fn()}
        onRenameConversation={vi.fn()}
        thinkingEnabled={true}
        apiKey=""
        ownerId=""
        onApiKeyChange={vi.fn()}
        onOwnerIdChange={vi.fn()}
        systemInstruction="Be concise."
        onSystemInstructionChange={vi.fn()}
        onExportMarkdown={vi.fn()}
        onDeleteConversation={vi.fn()}
        advancedOpen={true}
        onAdvancedOpenChange={vi.fn()}
        temperature={0.7}
        onTemperatureChange={vi.fn()}
        maxTokens={4096}
        onMaxTokensChange={vi.fn()}
        topP={0.9}
        onTopPChange={vi.fn()}
        onResetAdvanced={vi.fn()}
        {...buildSharedAccessProps()}
      />,
    )

    const badges = screen.getAllByTestId('model-capability-badge')
    expect(badges).toHaveLength(2)
    expect(badges.map(node => node.textContent)).toEqual(['Thinking', 'Vision'])
    expect(screen.getByText('+1')).toBeInTheDocument()
    expect(screen.getByLabelText(/model capabilities: thinking \/ vision \/ tools/i)).toBeInTheDocument()
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument()
  })

  it('passes desktop diagnostics through to the settings panel', () => {
    render(
      <TopBar
        sessionTitle="Strategy Sync"
        hasSession={true}
        modelCapabilities={['completion', 'tools']}
        appearanceSummary="Classic System"
        desktopDiagnostics={{
          desktop_mode: true,
          backend_base_url: 'http://127.0.0.1:62606',
          readiness_ok: true,
          failing_checks: [],
          skipped_checks: [],
          code_sandbox_effective_enabled: true,
          workbench_effective_enabled: true,
          app_data_dir: 'C:/GOAT/Desktop',
          runtime_root: 'C:/GOAT/Desktop',
          data_dir: 'C:/GOAT/Desktop/data',
          log_dir: 'C:/GOAT/Desktop/logs',
          log_db_path: 'C:/GOAT/Desktop/chat_logs.db',
          packaged_shell_log_path: 'C:/GOAT/Desktop/logs/desktop-shell.log',
        }}
        desktopDiagnosticsError={null}
        onOpenAppearance={vi.fn()}
        onRenameConversation={vi.fn()}
        thinkingEnabled={false}
        apiKey=""
        ownerId=""
        onApiKeyChange={vi.fn()}
        onOwnerIdChange={vi.fn()}
        systemInstruction=""
        onSystemInstructionChange={vi.fn()}
        onExportMarkdown={vi.fn()}
        onDeleteConversation={vi.fn()}
        advancedOpen={false}
        onAdvancedOpenChange={vi.fn()}
        temperature={0.7}
        onTemperatureChange={vi.fn()}
        maxTokens={4096}
        onMaxTokensChange={vi.fn()}
        topP={0.9}
        onTopPChange={vi.fn()}
        onResetAdvanced={vi.fn()}
        {...buildSharedAccessProps()}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: /settings/i }))

    expect(screen.getByText('Desktop runtime')).toBeInTheDocument()
    expect(screen.getByText('http://127.0.0.1:62606')).toBeInTheDocument()
    expect(screen.getByText('C:/GOAT/Desktop/logs/desktop-shell.log')).toBeInTheDocument()
  })
})
