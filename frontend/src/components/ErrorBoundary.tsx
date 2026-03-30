import { Component, type ErrorInfo, type ReactNode } from 'react'

interface Props {
  children: ReactNode
  /** Optional custom fallback. If omitted, the default full-page fallback is shown. */
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

/**
 * Catches synchronous rendering errors in the React tree and shows a
 * friendly recovery UI instead of a blank white page.
 */
export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  override componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error('[ErrorBoundary]', error, info.componentStack)
  }

  private handleReset = (): void => {
    this.setState({ hasError: false, error: null })
  }

  override render(): ReactNode {
    if (!this.state.hasError) return this.props.children

    if (this.props.fallback) return this.props.fallback

    return (
      <div
        className="flex flex-col items-center justify-center h-full gap-5 p-8 text-center"
        style={{ background: 'var(--bg-chat)' }}
      >
        <div
          className="w-16 h-16 rounded-2xl flex items-center justify-center text-3xl"
          style={{ background: 'rgba(239,68,68,0.1)' }}
        >
          ⚠️
        </div>
        <div>
          <h2 className="text-lg font-bold mb-1" style={{ color: 'var(--text-main)' }}>
            Something went wrong
          </h2>
          <p className="text-sm max-w-sm" style={{ color: 'var(--text-muted)' }}>
            An unexpected error occurred in the UI. Your conversation is safe —
            click below to recover.
          </p>
          {this.state.error && (
            <details className="mt-3 text-xs text-left" style={{ color: 'var(--text-muted)' }}>
              <summary className="cursor-pointer hover:underline">Technical details</summary>
              <pre className="mt-1 p-2 rounded overflow-x-auto"
                style={{ background: 'var(--bg-asst-bubble)' }}>
                {this.state.error.message}
              </pre>
            </details>
          )}
        </div>
        <div className="flex gap-3">
          <button
            type="button"
            onClick={this.handleReset}
            className="px-4 py-2 rounded-lg text-sm font-semibold transition-all"
            style={{ background: 'var(--navy)', color: '#fff' }}
          >
            Try again
          </button>
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="px-4 py-2 rounded-lg text-sm transition-all"
            style={{ border: '1px solid var(--border-color)', color: 'var(--text-main)' }}
          >
            Reload page
          </button>
        </div>
      </div>
    )
  }
}
