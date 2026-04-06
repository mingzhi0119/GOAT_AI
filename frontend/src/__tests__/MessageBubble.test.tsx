import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import MessageBubble from '../components/MessageBubble'

describe('MessageBubble', () => {
  it('renders visible user message content', () => {
    render(
      <MessageBubble message={{ id: 'm1', role: 'user', content: 'Hello from user' }} />,
    )
    expect(screen.getByText('Hello from user')).toBeInTheDocument()
  })
})
