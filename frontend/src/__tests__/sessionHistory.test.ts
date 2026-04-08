import { describe, expect, it } from 'vitest'
import { hydrateHistorySession, FILE_CONTEXT_REPLY } from '../utils/sessionHistory'

describe('session history utils', () => {
  it('hydrates normalized history details into visible and hidden chat rows', () => {
    const messages = hydrateHistorySession({
      id: 's1',
      title: 'Chart run',
      model: 'm',
      created_at: 'c',
      updated_at: 'u',
      file_context: { prompt: '[User uploaded tabular data for analysis]\n\nCHART_DATA_CSV:\n```csv```' },
      knowledge_documents: [],
      chart_spec: null,
      messages: [
        { role: 'user', content: 'Please chart revenue.' },
        { role: 'assistant', content: 'Done.' },
      ],
    })

    expect(messages).toHaveLength(4)
    expect(messages[0]).toMatchObject({ role: 'user', hidden: true, file_context: true })
    expect(messages[1]).toMatchObject({
      role: 'assistant',
      content: FILE_CONTEXT_REPLY,
      hidden: true,
    })
    expect(messages[2]).toMatchObject({ role: 'user', content: 'Please chart revenue.' })
    expect(messages[3]).toMatchObject({ role: 'assistant', content: 'Done.' })
  })
})
