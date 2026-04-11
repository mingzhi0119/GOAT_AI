import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ErrorBoundary } from '../components/ErrorBoundary'

class Boom extends Error {
  constructor() {
    super('boom')
  }
}

function Thrower(): null {
  throw new Boom()
}

describe('ErrorBoundary', () => {
  it('renders the default fallback and technical details when a child throws', () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined)

    render(
      <ErrorBoundary>
        <Thrower />
      </ErrorBoundary>,
    )

    expect(screen.getByText('Something went wrong')).toBeInTheDocument()
    expect(screen.getByText(/Your conversation is safe - click below to recover/i)).toBeInTheDocument()
    expect(screen.getByText('Technical details')).toBeInTheDocument()
    expect(screen.getByText('boom')).toBeInTheDocument()

    consoleError.mockRestore()
  })

  it('renders a custom fallback when provided', () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined)

    render(
      <ErrorBoundary fallback={<div>Custom fallback</div>}>
        <Thrower />
      </ErrorBoundary>,
    )

    expect(screen.getByText('Custom fallback')).toBeInTheDocument()

    consoleError.mockRestore()
  })

  it('reloads the page from the fallback action', () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined)
    const reload = vi.fn()
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: { ...window.location, reload },
    })

    render(
      <ErrorBoundary>
        <Thrower />
      </ErrorBoundary>,
    )

    fireEvent.click(screen.getByRole('button', { name: /reload page/i }))
    expect(reload).toHaveBeenCalled()

    consoleError.mockRestore()
  })
})
