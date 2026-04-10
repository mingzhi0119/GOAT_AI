import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import TopBar from '../components/TopBar'

function renderTopBar() {
  const onOpenAppearance = vi.fn()
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
      modelCapabilities={['completion', 'tools', 'vision']}
      appearanceSummary="Classic System"
      onOpenAppearance={onOpenAppearance}
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
  }
}

describe('TopBar options callout', () => {
  it('shows the session title on the left and model skills beside it', () => {
    renderTopBar()

    expect(screen.getByRole('heading', { name: 'Strategy Sync' })).toHaveStyle({
      color: 'var(--text-main)',
    })
    expect(screen.queryByText('Skills')).not.toBeInTheDocument()
    expect(screen.getByText('Tools')).toBeInTheDocument()
    expect(screen.getByText('Vision')).toBeInTheDocument()
  })

  it('opens the options callout and no longer shows legacy helper copy', () => {
    renderTopBar()

    fireEvent.click(screen.getByRole('button', { name: /options/i }))

    expect(screen.getByRole('dialog', { name: /options/i })).toBeInTheDocument()
    expect(screen.queryByText(/Enter sends the message/i)).not.toBeInTheDocument()
    expect(screen.getByText(/^Generation$/)).toBeInTheDocument()
  })

  it('removes the max-token helper copy from the options panel', () => {
    renderTopBar()
    fireEvent.click(screen.getByRole('button', { name: /options/i }))
    expect(screen.queryByText(/API allows up to 131,072 generation tokens/i)).not.toBeInTheDocument()
  })

  it('keeps system instruction editing and clear actions wired', () => {
    const { onSystemInstructionChange } = renderTopBar()

    fireEvent.click(screen.getByRole('button', { name: /options/i }))
    fireEvent.change(screen.getByPlaceholderText(/optional: tone, format, or constraints/i), {
      target: { value: 'Use bullets.' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Clear' }))

    expect(onSystemInstructionChange).toHaveBeenCalledWith('Use bullets.')
    expect(onSystemInstructionChange).toHaveBeenCalledWith('')
  })

  it('keeps generation settings, appearance, export, and delete actions wired', () => {
    const {
      onTemperatureChange,
      onMaxTokensChange,
      onTopPChange,
      onResetAdvanced,
      onExportMarkdown,
      onDeleteConversation,
      onOpenAppearance,
    } = renderTopBar()

    fireEvent.click(screen.getByRole('button', { name: /options/i }))

    const inputs = screen.getAllByRole('spinbutton')
    fireEvent.change(inputs[0]!, { target: { value: '1.1' } })
    fireEvent.change(inputs[1]!, { target: { value: '999999' } })
    fireEvent.change(inputs[2]!, { target: { value: '0.8' } })
    fireEvent.click(screen.getByRole('button', { name: /reset generation settings to defaults/i }))
    fireEvent.click(screen.getByText('Classic System').closest('button') as HTMLButtonElement)
    fireEvent.click(screen.getByRole('button', { name: /conversation actions/i }))
    fireEvent.click(screen.getByRole('menuitem', { name: /export to markdown/i }))
    fireEvent.click(screen.getByRole('button', { name: /conversation actions/i }))
    fireEvent.click(screen.getByRole('menuitem', { name: /delete/i }))

    expect(onTemperatureChange).toHaveBeenCalledWith(1.1)
    expect(onMaxTokensChange).toHaveBeenCalledWith(131072)
    expect(onTopPChange).toHaveBeenCalledWith(0.8)
    expect(onResetAdvanced).toHaveBeenCalled()
    expect(onExportMarkdown).toHaveBeenCalled()
    expect(onDeleteConversation).toHaveBeenCalled()
    expect(onOpenAppearance).toHaveBeenCalled()
  })

  it('removes export from options and places conversation actions in the ellipsis menu', () => {
    renderTopBar()

    fireEvent.click(screen.getByRole('button', { name: /options/i }))
    expect(screen.queryByRole('button', { name: /export markdown/i })).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /conversation actions/i }))
    expect(screen.getByRole('menu', { name: /conversation actions/i })).toBeInTheDocument()
    expect(screen.getByRole('menuitem', { name: /export to markdown/i })).toBeInTheDocument()
    expect(screen.getByRole('menuitem', { name: /delete/i })).toBeInTheDocument()
  })
})
