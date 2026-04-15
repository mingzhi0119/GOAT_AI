/* @vitest-environment jsdom */
import { act, renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useChatSession } from '../hooks/useChatSession'

const sendMessageMock = vi.fn()
const stopStreamingMock = vi.fn()
const refreshHistoryMock = vi.fn().mockResolvedValue(undefined)
const upsertHistorySessionMock = vi.fn()
const loadHistoryMock = vi.fn()
const deleteSessionMock = vi.fn()
const deleteAllMock = vi.fn()
const renameSessionMock = vi.fn()

vi.mock('../hooks/useChat', async () => {
  const React = await import('react')
  return {
    useChat: () => {
      const [sessionId, setSessionId] = React.useState<string | null>(null)
      const clearMessagesMock = vi.fn(() => {
        setSessionId(null)
      })
      const loadSessionMock = vi.fn((session: { id: string }) => {
        setSessionId(session.id)
      })

      return {
        messages: [],
        isStreaming: false,
        sessionId,
        sendMessage: async (...args: unknown[]) => {
          const activeSessionId = args[10] as string
          setSessionId(activeSessionId)
          sendMessageMock(...args)
          return activeSessionId
        },
        streamToChat: vi.fn(),
        clearMessages: clearMessagesMock,
        stopStreaming: stopStreamingMock,
        loadSession: loadSessionMock,
      }
    },
  }
})

vi.mock('../hooks/useHistory', () => ({
  useHistory: () => ({
    sessions: [],
    isLoading: false,
    error: null,
    refresh: refreshHistoryMock,
    upsertSession: upsertHistorySessionMock,
    loadSession: loadHistoryMock,
    deleteSession: deleteSessionMock,
    deleteAll: deleteAllMock,
    renameSession: renameSessionMock,
  }),
}))

describe('useChatSession', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('attaches the knowledge document id when the file context is ready', async () => {
    const { result } = renderHook(() =>
      useChatSession({
        selectedModel: 'test-model',
        userName: 'Simon',
        systemInstruction: '',
        planModeEnabled: false,
        themeStyle: 'urochester',
      }),
    )

    act(() => {
      result.current.upsertFileContext({
        filename: 'Quiz4_Cheat_Sheet.md',
        documentId: 'doc-quiz-4',
        bindingMode: 'single',
        status: 'ready',
      })
    })

    await act(async () => {
      await result.current.sendMessage('Use the uploaded file')
    })

    expect(sendMessageMock).toHaveBeenCalledWith(
      'Use the uploaded file',
      'test-model',
      'Simon',
      ['doc-quiz-4'],
      false,
      '',
      'urochester',
      undefined,
      expect.any(Function),
      undefined,
      expect.any(String),
    )
    expect(upsertHistorySessionMock).toHaveBeenCalledTimes(1)
  })

  it('locks persona snapshot after the first send in the active chat', async () => {
    const initialProps: { systemInstruction: string; themeStyle: 'urochester' | 'thu' } = {
      systemInstruction: '',
      themeStyle: 'urochester',
    }
    const { result, rerender } = renderHook(
      (props: { systemInstruction: string; themeStyle: 'urochester' | 'thu' }) =>
        useChatSession({
          selectedModel: 'test-model',
          userName: 'Simon',
          systemInstruction: props.systemInstruction,
          planModeEnabled: false,
          themeStyle: props.themeStyle,
        }),
      {
        initialProps,
      },
    )

    await act(async () => {
      await result.current.sendMessage('First turn')
    })

    rerender({
      systemInstruction: 'Be extra formal.',
      themeStyle: 'thu',
    })

    await act(async () => {
      await result.current.sendMessage('Second turn')
    })

    expect(sendMessageMock).toHaveBeenNthCalledWith(
      2,
      'Second turn',
      'test-model',
      'Simon',
      undefined,
      false,
      '',
      'urochester',
      undefined,
      expect.any(Function),
      undefined,
      expect.any(String),
    )
    expect(result.current.personaStatusMessage).toBe('Theme and instruction changes apply to new chats.')
  })

  it('clears the locked persona snapshot when starting a new chat', async () => {
    const initialProps: { systemInstruction: string; themeStyle: 'urochester' | 'thu' } = {
      systemInstruction: '',
      themeStyle: 'urochester',
    }
    const { result, rerender } = renderHook(
      (props: { systemInstruction: string; themeStyle: 'urochester' | 'thu' }) =>
        useChatSession({
          selectedModel: 'test-model',
          userName: 'Simon',
          systemInstruction: props.systemInstruction,
          planModeEnabled: false,
          themeStyle: props.themeStyle,
        }),
      {
        initialProps,
      },
    )

    await act(async () => {
      await result.current.sendMessage('First turn')
    })

    rerender({
      systemInstruction: 'Be extra formal.',
      themeStyle: 'thu',
    })

    act(() => {
      result.current.clearChatSession()
    })

    await act(async () => {
      await result.current.sendMessage('Fresh chat')
    })

    expect(sendMessageMock).toHaveBeenNthCalledWith(
      2,
      'Fresh chat',
      'test-model',
      'Simon',
      undefined,
      false,
      'Be extra formal.',
      'thu',
      undefined,
      expect.any(Function),
      undefined,
      expect.any(String),
    )
  })

  it('does not pretend an unfinished file upload is attached', async () => {
    const { result } = renderHook(() =>
      useChatSession({
        selectedModel: 'test-model',
        userName: 'Simon',
        systemInstruction: '',
        planModeEnabled: false,
        themeStyle: 'urochester',
      }),
    )

    act(() => {
      result.current.upsertFileContext({
        filename: 'Quiz4_Cheat_Sheet.md',
        bindingMode: 'single',
        status: 'processing',
      })
    })

    await act(async () => {
      await result.current.sendMessage('Try without a ready document id')
    })

    expect(sendMessageMock).toHaveBeenCalledWith(
      'Try without a ready document id',
      'test-model',
      'Simon',
      undefined,
      false,
      '',
      'urochester',
      undefined,
      expect.any(Function),
      undefined,
      expect.any(String),
    )
    expect(upsertHistorySessionMock).toHaveBeenCalledTimes(1)
  })

  it('does not attach knowledge documents when image attachments are present', async () => {
    const { result } = renderHook(() =>
      useChatSession({
        selectedModel: 'test-model',
        userName: 'Simon',
        systemInstruction: '',
        planModeEnabled: false,
        themeStyle: 'urochester',
      }),
    )

    act(() => {
      result.current.upsertFileContext({
        filename: 'Quiz4_Cheat_Sheet.md',
        documentId: 'doc-quiz-4',
        bindingMode: 'single',
        status: 'ready',
      })
    })

    await act(async () => {
      await result.current.sendMessage('Use the uploaded file', ['img-1'])
    })

    expect(sendMessageMock).toHaveBeenCalledWith(
      'Use the uploaded file',
      'test-model',
      'Simon',
      undefined,
      false,
      '',
      'urochester',
      undefined,
      expect.any(Function),
      ['img-1'],
      expect.any(String),
    )
  })

  it('restores persona snapshot from history when available', async () => {
    loadHistoryMock.mockResolvedValueOnce({
      id: 'session-1',
      title: 'Saved session',
      model: 'test-model',
      schema_version: 1,
      created_at: '2026-04-13T00:00:00Z',
      updated_at: '2026-04-13T00:00:01Z',
      owner_id: 'owner-1',
      messages: [],
      persona_snapshot: {
        theme_style: 'classic',
        system_instruction: 'Use short bullets.',
      },
      chart_spec: null,
      file_context: null,
      knowledge_documents: [],
      workspace_outputs: [],
      chart_data_source: null,
    })

    const { result } = renderHook(() =>
      useChatSession({
        selectedModel: 'test-model',
        userName: 'Simon',
        systemInstruction: 'Ignored after restore',
        planModeEnabled: false,
        themeStyle: 'thu',
      }),
    )

    await act(async () => {
      await result.current.loadHistorySession('session-1')
    })
    await act(async () => {
      await result.current.sendMessage('Continue saved chat')
    })

    expect(sendMessageMock).toHaveBeenCalledWith(
      'Continue saved chat',
      'test-model',
      'Simon',
      undefined,
      false,
      'Use short bullets.',
      'classic',
      undefined,
      expect.any(Function),
      undefined,
      'session-1',
    )
  })

  it('falls back to current settings for legacy history sessions without a snapshot', async () => {
    loadHistoryMock.mockResolvedValueOnce({
      id: 'session-1',
      title: 'Saved session',
      model: 'test-model',
      schema_version: 1,
      created_at: '2026-04-13T00:00:00Z',
      updated_at: '2026-04-13T00:00:01Z',
      owner_id: 'owner-1',
      messages: [],
      persona_snapshot: null,
      chart_spec: null,
      file_context: null,
      knowledge_documents: [],
      workspace_outputs: [],
      chart_data_source: null,
    })

    const { result } = renderHook(() =>
      useChatSession({
        selectedModel: 'test-model',
        userName: 'Simon',
        systemInstruction: 'Use current defaults.',
        planModeEnabled: false,
        themeStyle: 'thu',
      }),
    )

    await act(async () => {
      await result.current.loadHistorySession('session-1')
    })
    await act(async () => {
      await result.current.sendMessage('Continue legacy chat')
    })

    expect(sendMessageMock).toHaveBeenCalledWith(
      'Continue legacy chat',
      'test-model',
      'Simon',
      undefined,
      false,
      'Use current defaults.',
      'thu',
      undefined,
      expect.any(Function),
      undefined,
      'session-1',
    )
    expect(result.current.personaStatusMessage).toMatch(/older chat/i)
  })

  it('clears stale file contexts when a history session has no knowledge attachments', async () => {
    loadHistoryMock.mockResolvedValueOnce({
      id: 'session-1',
      title: 'Saved session',
      model: 'test-model',
      schema_version: 1,
      created_at: '2026-04-13T00:00:00Z',
      updated_at: '2026-04-13T00:00:01Z',
      owner_id: 'owner-1',
      messages: [],
      persona_snapshot: null,
      chart_spec: null,
      file_context: null,
      knowledge_documents: [],
      workspace_outputs: [],
      chart_data_source: null,
    })

    const { result } = renderHook(() =>
      useChatSession({
        selectedModel: 'test-model',
        userName: 'Simon',
        systemInstruction: '',
        planModeEnabled: false,
        themeStyle: 'urochester',
      }),
    )

    act(() => {
      result.current.upsertFileContext({
        filename: 'Stale.md',
        documentId: 'doc-stale',
        bindingMode: 'single',
        status: 'ready',
      })
    })

    expect(result.current.fileContexts).toHaveLength(1)

    await act(async () => {
      await result.current.loadHistorySession('session-1')
    })

    expect(loadHistoryMock).toHaveBeenCalledWith('session-1')
    expect(result.current.fileContexts).toEqual([])
  })
})
