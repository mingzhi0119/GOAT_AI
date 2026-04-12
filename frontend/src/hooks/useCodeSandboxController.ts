import { useCallback, useEffect, useRef, useState } from 'react'
import {
  executeCodeSandbox,
  fetchCodeSandboxExecution,
  openCodeSandboxLogStream,
} from '../api/codeSandbox'
import type {
  CodeSandboxExecutionMode,
  CodeSandboxExecutionResponse,
  CodeSandboxFeature,
} from '../api/types'

interface UseCodeSandboxControllerReturn {
  codeSandboxEnabled: boolean
  sandboxCode: string
  sandboxCommand: string
  sandboxError: string | null
  sandboxExecutionMode: CodeSandboxExecutionMode
  sandboxLiveLogs: string[]
  sandboxPending: boolean
  sandboxResult: CodeSandboxExecutionResponse | null
  sandboxStdin: string
  sandboxStreamDisconnected: boolean
  clearSandboxError: () => void
  runCodeSandbox: () => Promise<void>
  setSandboxCode: (value: string) => void
  setSandboxCommand: (value: string) => void
  setSandboxExecutionMode: (value: CodeSandboxExecutionMode) => void
  setSandboxStdin: (value: string) => void
  stopCodeSandboxMonitoring: () => void
}

export function useCodeSandboxController(
  codeSandboxFeature: CodeSandboxFeature | null,
): UseCodeSandboxControllerReturn {
  const [sandboxExecutionMode, setSandboxExecutionMode] = useState<CodeSandboxExecutionMode>('sync')
  const [sandboxCode, setSandboxCode] = useState('')
  const [sandboxCommand, setSandboxCommand] = useState('')
  const [sandboxStdin, setSandboxStdin] = useState('')
  const [sandboxPending, setSandboxPending] = useState(false)
  const [sandboxError, setSandboxError] = useState<string | null>(null)
  const [sandboxResult, setSandboxResult] = useState<CodeSandboxExecutionResponse | null>(null)
  const [sandboxLiveLogs, setSandboxLiveLogs] = useState<string[]>([])
  const [sandboxStreamDisconnected, setSandboxStreamDisconnected] = useState(false)
  const sandboxLogCloseRef = useRef<(() => void) | null>(null)
  const sandboxPollRef = useRef<number | null>(null)
  const sandboxLogCursorRef = useRef(0)

  const codeSandboxEnabled =
    !!codeSandboxFeature?.policy_allowed && !!codeSandboxFeature?.effective_enabled

  const stopSandboxPolling = useCallback(() => {
    if (sandboxPollRef.current !== null) {
      window.clearInterval(sandboxPollRef.current)
      sandboxPollRef.current = null
    }
  }, [])

  const stopSandboxLogStream = useCallback(() => {
    sandboxLogCloseRef.current?.()
    sandboxLogCloseRef.current = null
  }, [])

  const refreshSandboxExecution = useCallback(
    async (executionId: string) => {
      const execution = await fetchCodeSandboxExecution(executionId)
      setSandboxResult(current => {
        if (!current || current.execution_id !== executionId) return execution
        return execution
      })
      if (
        execution.status === 'completed' ||
        execution.status === 'failed' ||
        execution.status === 'denied'
      ) {
        stopSandboxPolling()
        stopSandboxLogStream()
      }
    },
    [stopSandboxLogStream, stopSandboxPolling],
  )

  const startSandboxPolling = useCallback(
    (executionId: string) => {
      stopSandboxPolling()
      sandboxPollRef.current = window.setInterval(() => {
        void refreshSandboxExecution(executionId).catch(() => {
          // Keep polling; the inline status copy is enough here.
        })
      }, 1000)
    },
    [refreshSandboxExecution, stopSandboxPolling],
  )

  const startSandboxLogStream = useCallback(
    (executionId: string) => {
      stopSandboxLogStream()
      setSandboxStreamDisconnected(false)
      sandboxLogCloseRef.current = openCodeSandboxLogStream(executionId, {
        afterSequence: sandboxLogCursorRef.current,
        onEvent: event => {
          if (event.type === 'stdout' || event.type === 'stderr') {
            if (typeof event.sequence === 'number') {
              sandboxLogCursorRef.current = Math.max(sandboxLogCursorRef.current, event.sequence)
            }
            const chunk = event.chunk
            if (typeof chunk === 'string' && chunk.length > 0) {
              setSandboxLiveLogs(prev => [...prev, chunk])
            }
            return
          }
          if (event.type === 'status') {
            setSandboxResult(current => {
              if (!current || current.execution_id !== executionId) return current
              return {
                ...current,
                status: event.status ?? current.status,
                provider_name: event.provider_name ?? current.provider_name,
                updated_at: event.updated_at ?? current.updated_at,
                timed_out: event.timed_out ?? current.timed_out,
              }
            })
            return
          }
          if (event.type === 'done') {
            stopSandboxLogStream()
            void refreshSandboxExecution(executionId).catch(() => {
              startSandboxPolling(executionId)
            })
          }
        },
        onError: () => {
          setSandboxStreamDisconnected(true)
          startSandboxPolling(executionId)
        },
      })
    },
    [refreshSandboxExecution, startSandboxPolling, stopSandboxLogStream],
  )

  useEffect(() => {
    return () => {
      stopSandboxLogStream()
      stopSandboxPolling()
    }
  }, [stopSandboxLogStream, stopSandboxPolling])

  const clearSandboxError = useCallback(() => {
    setSandboxError(null)
  }, [])

  const stopCodeSandboxMonitoring = useCallback(() => {
    stopSandboxLogStream()
    stopSandboxPolling()
  }, [stopSandboxLogStream, stopSandboxPolling])

  const runCodeSandbox = useCallback(async () => {
    if ((!sandboxCode.trim() && !sandboxCommand.trim()) || sandboxPending || !codeSandboxEnabled) {
      return
    }
    setSandboxPending(true)
    setSandboxError(null)
    setSandboxLiveLogs([])
    setSandboxStreamDisconnected(false)
    sandboxLogCursorRef.current = 0
    stopSandboxPolling()
    stopSandboxLogStream()
    try {
      const result = await executeCodeSandbox({
        execution_mode: sandboxExecutionMode,
        runtime_preset: 'shell',
        ...(sandboxCode.trim() ? { code: sandboxCode } : {}),
        ...(sandboxCommand.trim() ? { command: sandboxCommand.trim() } : {}),
        ...(sandboxStdin ? { stdin: sandboxStdin } : {}),
      })
      setSandboxResult(result)
      if (
        result.execution_mode === 'async' &&
        (result.status === 'queued' || result.status === 'running')
      ) {
        startSandboxLogStream(result.execution_id)
      }
    } catch (error) {
      setSandboxError(error instanceof Error ? error.message : 'Code sandbox execution failed')
      setSandboxResult(null)
    } finally {
      setSandboxPending(false)
    }
  }, [
    codeSandboxEnabled,
    sandboxCode,
    sandboxCommand,
    sandboxExecutionMode,
    sandboxPending,
    sandboxStdin,
    startSandboxLogStream,
    stopSandboxLogStream,
    stopSandboxPolling,
  ])

  return {
    codeSandboxEnabled,
    sandboxCode,
    sandboxCommand,
    sandboxError,
    sandboxExecutionMode,
    sandboxLiveLogs,
    sandboxPending,
    sandboxResult,
    sandboxStdin,
    sandboxStreamDisconnected,
    clearSandboxError,
    runCodeSandbox,
    setSandboxCode,
    setSandboxCommand,
    setSandboxExecutionMode,
    setSandboxStdin,
    stopCodeSandboxMonitoring,
  }
}
