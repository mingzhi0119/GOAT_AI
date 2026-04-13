import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { createRef } from 'react'
import { describe, expect, it, vi } from 'vitest'
import PlusMenu from '../components/PlusMenu'

describe('PlusMenu', () => {
  it('renders actions and toggles plan/thinking state when available', () => {
    const onOpenCodeSandbox = vi.fn()
    const onUploadFiles = vi.fn()
    const onOpenManageUploads = vi.fn()
    const onTogglePlanMode = vi.fn()
    const onToggleThinkingMode = vi.fn()

    render(
        <PlusMenu
          isOpen={true}
          isNarrow={false}
          panelId="plus-menu"
          codeSandboxFeature={{
            policy_allowed: true,
            allowed_by_config: true,
          available_on_host: true,
          effective_enabled: true,
          provider_name: 'docker',
          isolation_level: 'container',
          network_policy_enforced: true,
          deny_reason: null,
        }}
          planModeEnabled={true}
          supportsThinking={true}
          thinkingEnabled={false}
          onClose={vi.fn()}
          onOpenCodeSandbox={onOpenCodeSandbox}
          onUploadFiles={onUploadFiles}
          onOpenManageUploads={onOpenManageUploads}
        onTogglePlanMode={onTogglePlanMode}
        onToggleThinkingMode={onToggleThinkingMode}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: /upload files/i }))
    fireEvent.click(screen.getByRole('button', { name: /open code sandbox/i }))
    fireEvent.click(screen.getByRole('button', { name: /manage uploads/i }))
    fireEvent.click(screen.getByRole('switch', { name: /plan mode/i }))
    fireEvent.click(screen.getByRole('switch', { name: /thinking mode/i }))

    expect(onUploadFiles).toHaveBeenCalled()
    expect(onOpenCodeSandbox).toHaveBeenCalled()
    expect(onOpenManageUploads).toHaveBeenCalled()
    expect(onTogglePlanMode).toHaveBeenCalled()
    expect(onToggleThinkingMode).toHaveBeenCalled()
  })

  it('disables the code sandbox action when unavailable', () => {
    render(
        <PlusMenu
          isOpen={true}
          isNarrow={true}
          panelId="plus-menu"
          codeSandboxFeature={{
            policy_allowed: false,
            allowed_by_config: true,
          available_on_host: false,
          effective_enabled: false,
          provider_name: 'docker',
          isolation_level: 'container',
          network_policy_enforced: true,
          deny_reason: 'disabled_by_operator',
        }}
        planModeEnabled={false}
        supportsThinking={false}
        thinkingEnabled={false}
        onClose={vi.fn()}
        onOpenCodeSandbox={vi.fn()}
        onUploadFiles={vi.fn()}
        onOpenManageUploads={vi.fn()}
        onTogglePlanMode={vi.fn()}
        onToggleThinkingMode={vi.fn()}
      />,
    )

    expect(screen.getByRole('button', { name: /code sandbox unavailable/i })).toBeDisabled()
  })

  it('keeps plan mode read-only when backend capability is unavailable', () => {
    const onTogglePlanMode = vi.fn()

    render(
      <PlusMenu
        isOpen={true}
        isNarrow={false}
        panelId="plus-menu"
        codeSandboxFeature={{
          policy_allowed: true,
          allowed_by_config: true,
          available_on_host: true,
          effective_enabled: true,
          provider_name: 'docker',
          isolation_level: 'container',
          network_policy_enforced: true,
          deny_reason: null,
        }}
        planModeEnabled={false}
        planModeAvailability="Disabled in this deployment configuration"
        planModeFeature={{
          allowed_by_config: false,
          available_on_host: true,
          effective_enabled: false,
          deny_reason: null,
        }}
        supportsThinking={false}
        thinkingEnabled={false}
        onClose={vi.fn()}
        onOpenCodeSandbox={vi.fn()}
        onUploadFiles={vi.fn()}
        onOpenManageUploads={vi.fn()}
        onTogglePlanMode={onTogglePlanMode}
        onToggleThinkingMode={vi.fn()}
      />,
    )

    const planSwitch = screen.getByRole('switch', { name: /plan mode unavailable/i })
    expect(planSwitch).toBeDisabled()
    expect(screen.getByText('Disabled in this deployment configuration')).toBeInTheDocument()

    fireEvent.click(planSwitch)
    expect(onTogglePlanMode).not.toHaveBeenCalled()
  })

  it('renders larger chevrons for submenu-style actions', () => {
    const { container } = render(
        <PlusMenu
          isOpen={true}
          isNarrow={false}
          panelId="plus-menu"
          codeSandboxFeature={{
            policy_allowed: true,
            allowed_by_config: true,
          available_on_host: true,
          effective_enabled: true,
          provider_name: 'docker',
          isolation_level: 'container',
          network_policy_enforced: true,
          deny_reason: null,
        }}
        planModeEnabled={false}
        supportsThinking={false}
        thinkingEnabled={false}
        onClose={vi.fn()}
        onOpenCodeSandbox={vi.fn()}
        onUploadFiles={vi.fn()}
        onOpenManageUploads={vi.fn()}
        onTogglePlanMode={vi.fn()}
        onToggleThinkingMode={vi.fn()}
      />,
    )

    expect(container.querySelectorAll('svg.h-\\[18px\\].w-\\[18px\\]').length).toBe(2)
  })

  it('focuses the first action on open and restores trigger focus on Escape', async () => {
    const onClose = vi.fn()
    const triggerRef = createRef<HTMLButtonElement>()

    render(
      <>
        <button ref={triggerRef} type="button">
          Open actions
        </button>
        <PlusMenu
          isOpen={true}
          isNarrow={false}
          panelId="plus-menu"
          triggerRef={triggerRef}
          codeSandboxFeature={{
            policy_allowed: true,
            allowed_by_config: true,
            available_on_host: true,
            effective_enabled: true,
            provider_name: 'docker',
            isolation_level: 'container',
            network_policy_enforced: true,
            deny_reason: null,
          }}
          planModeEnabled={false}
          supportsThinking={false}
          thinkingEnabled={false}
          onClose={onClose}
          onOpenCodeSandbox={vi.fn()}
          onUploadFiles={vi.fn()}
          onOpenManageUploads={vi.fn()}
          onTogglePlanMode={vi.fn()}
          onToggleThinkingMode={vi.fn()}
        />
      </>,
    )

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /upload files/i })).toHaveFocus()
    })

    fireEvent.keyDown(screen.getByRole('dialog', { name: /upload and planning actions/i }), {
      key: 'Escape',
    })

    expect(onClose).toHaveBeenCalled()
    await waitFor(() => {
      expect(triggerRef.current).toHaveFocus()
    })
  })
})
