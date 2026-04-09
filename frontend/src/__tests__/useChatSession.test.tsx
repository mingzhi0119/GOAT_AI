/* @vitest-environment jsdom */
import { act, renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useChatSession } from '../hooks/useChatSession'

const sendMessageMock = vi.fn()
const clearMessagesMock = vi.fn()
const loadSessionMock = vi.fn()
const stopStreamingMock = vi.fn()
const refreshHistoryMock = vi.fn().mockResolvedValue(undefined)
const loadHistoryMock = vi.fn()
const deleteSessionMock = vi.fn()
const deleteAllMock = vi.fn()

vi.mock('../hooks/useChat', () => ({
  useChat: () => ({
    messages: [],
    isStreaming: false,
    sessionId: null,
    sendMessage: sendMessageMock,
    streamToChat: vi.fn(),
    clearMessages: clearMessagesMock,
    stopStreaming: stopStreamingMock,
    loadSession: loadSessionMock,
  }),
}))

vi.mock('../hooks/useHistory', () => ({
  useHistory: () => ({
    sessions: [],
    isLoading: false,
    error: null,
    refresh: refreshHistoryMock,
    loadSession: loadHistoryMock,
    deleteSession: deleteSessionMock,
    deleteAll: deleteAllMock,
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
      '',
      undefined,
      expect.any(Function),
      undefined,
    )
  })

  it('does not pretend an unfinished file upload is attached', async () => {
    const { result } = renderHook(() =>
      useChatSession({
        selectedModel: 'test-model',
        userName: 'Simon',
        systemInstruction: '',
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
      '',
      undefined,
      expect.any(Function),
      undefined,
    )
  })
})
