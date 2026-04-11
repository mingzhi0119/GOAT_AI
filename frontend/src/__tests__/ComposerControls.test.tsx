import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import ComposerControls from '../components/ComposerControls'
import { getChatLayoutDecisions } from '../utils/chatLayout'

describe('ComposerControls', () => {
  it('wires the composer action buttons and toggles', () => {
    const onTogglePlusMenu = vi.fn()
    const onToggleModelMenu = vi.fn()
    const onToggleReasoningMenu = vi.fn()
    const onThinkingEnabledChange = vi.fn()
    const onPlanModeChange = vi.fn()
    const onSubmit = vi.fn()

    render(
      <ComposerControls
        layoutDecisions={getChatLayoutDecisions('wide')}
        selectedModel="gemma4:26b"
        reasoningLevel="medium"
        supportsThinking={true}
        thinkingEnabled={true}
        planModeEnabled={true}
        onPlanModeChange={onPlanModeChange}
        plusMenuOpen={false}
        modelMenuOpen={false}
        reasoningMenuOpen={false}
        isStreaming={false}
        attachmentUploading={false}
        canSend={true}
        gpuStatus={null}
        gpuError={null}
        inferenceLatency={null}
        onTogglePlusMenu={onTogglePlusMenu}
        onToggleModelMenu={onToggleModelMenu}
        onToggleReasoningMenu={onToggleReasoningMenu}
        onThinkingEnabledChange={onThinkingEnabledChange}
        onStop={vi.fn()}
        onSubmit={onSubmit}
      />,
    )

    fireEvent.click(screen.getByTitle(/open upload and planning actions/i))
    fireEvent.click(screen.getByRole('button', { name: /open model menu/i }))
    fireEvent.click(screen.getByRole('button', { name: /open reasoning menu/i }))
    fireEvent.click(screen.getByRole('button', { name: /plan enabled/i }))
    fireEvent.click(screen.getByRole('button', { name: /thinking mode enabled/i }))
    fireEvent.click(screen.getByRole('button', { name: /send message/i }))

    expect(onTogglePlusMenu).toHaveBeenCalled()
    expect(onToggleModelMenu).toHaveBeenCalled()
    expect(onToggleReasoningMenu).toHaveBeenCalled()
    expect(onPlanModeChange).toHaveBeenCalledWith(false)
    expect(onThinkingEnabledChange).toHaveBeenCalledWith(false)
    expect(onSubmit).toHaveBeenCalled()
  })

  it('uses the stop action while streaming', () => {
    const onStop = vi.fn()

    render(
      <ComposerControls
        layoutDecisions={getChatLayoutDecisions('narrow')}
        selectedModel="gemma4:26b"
        reasoningLevel="high"
        supportsThinking={false}
        thinkingEnabled={false}
        planModeEnabled={false}
        onPlanModeChange={vi.fn()}
        plusMenuOpen={true}
        modelMenuOpen={true}
        reasoningMenuOpen={true}
        isStreaming={true}
        attachmentUploading={false}
        canSend={false}
        gpuStatus={null}
        gpuError={null}
        inferenceLatency={null}
        onTogglePlusMenu={vi.fn()}
        onToggleModelMenu={vi.fn()}
        onToggleReasoningMenu={vi.fn()}
        onThinkingEnabledChange={vi.fn()}
        onStop={onStop}
        onSubmit={vi.fn()}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: /stop generating/i }))
    expect(onStop).toHaveBeenCalled()
  })
})
