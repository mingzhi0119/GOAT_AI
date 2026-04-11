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
        systemInstruction="Be clear."
        temperature={0.7}
        maxTokens={1024}
        topP={0.9}
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
})
