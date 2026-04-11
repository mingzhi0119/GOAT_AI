import { fireEvent, render, screen } from '@testing-library/react'
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
        onOpenCodeSandbox={vi.fn()}
        onUploadFiles={vi.fn()}
        onOpenManageUploads={vi.fn()}
        onTogglePlanMode={vi.fn()}
        onToggleThinkingMode={vi.fn()}
      />,
    )

    expect(screen.getByRole('button', { name: /code sandbox unavailable/i })).toBeDisabled()
  })

  it('renders larger chevrons for submenu-style actions', () => {
    const { container } = render(
      <PlusMenu
        isOpen={true}
        isNarrow={false}
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
        onOpenCodeSandbox={vi.fn()}
        onUploadFiles={vi.fn()}
        onOpenManageUploads={vi.fn()}
        onTogglePlanMode={vi.fn()}
        onToggleThinkingMode={vi.fn()}
      />,
    )

    expect(container.querySelectorAll('svg.h-\\[18px\\].w-\\[18px\\]').length).toBe(2)
  })
})
