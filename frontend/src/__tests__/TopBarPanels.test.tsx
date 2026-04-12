import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ConversationActionsMenu, SettingsPanel } from '../components/TopBarPanels'

describe('TopBarPanels', () => {
  it('disables rename and delete when there is no saved session', () => {
    render(
      <ConversationActionsMenu
        hasSession={false}
        onRenameConversation={vi.fn()}
        onExportMarkdown={vi.fn()}
        onDeleteConversation={vi.fn()}
        onClose={vi.fn()}
        isNarrow={false}
      />,
    )

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
})
