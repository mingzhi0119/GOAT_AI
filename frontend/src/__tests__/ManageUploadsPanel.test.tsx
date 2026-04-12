import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import ManageUploadsPanel from '../components/ManageUploadsPanel'

describe('ManageUploadsPanel', () => {
  it('returns null when closed and shows empty state when open without files', () => {
    const { rerender } = render(
      <ManageUploadsPanel
        isOpen={false}
        uploadedKnowledgeFiles={[]}
        pendingImages={[]}
        onClose={vi.fn()}
        onRemoveFileContext={vi.fn()}
        onSetFileContextMode={vi.fn()}
        onRemovePendingImage={vi.fn()}
      />,
    )

    expect(screen.queryByText('Manage Uploads')).not.toBeInTheDocument()

    rerender(
      <ManageUploadsPanel
        isOpen={true}
        uploadedKnowledgeFiles={[]}
        pendingImages={[]}
        onClose={vi.fn()}
        onRemoveFileContext={vi.fn()}
        onSetFileContextMode={vi.fn()}
        onRemovePendingImage={vi.fn()}
      />,
    )

    expect(screen.getByText('No uploaded files yet.')).toBeInTheDocument()
  })

  it('wires knowledge file mode changes and delete actions', () => {
    const onRemoveFileContext = vi.fn()
    const onSetFileContextMode = vi.fn()
    const onClose = vi.fn()

    render(
      <ManageUploadsPanel
        isOpen={true}
        uploadedKnowledgeFiles={[
          { id: 'file-1', filename: 'report.pdf', status: 'ready', bindingMode: 'single' },
          { id: 'file-2', filename: 'draft.pdf', status: 'processing', bindingMode: 'idle' },
        ]}
        pendingImages={[]}
        onClose={onClose}
        onRemoveFileContext={onRemoveFileContext}
        onSetFileContextMode={onSetFileContextMode}
        onRemovePendingImage={vi.fn()}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: /close upload manager/i }))
    fireEvent.click(screen.getByRole('radio', { name: /sticky mode for report\.pdf/i }))
    fireEvent.click(screen.getByRole('button', { name: /delete report\.pdf/i }))

    expect(onClose).toHaveBeenCalled()
    expect(onSetFileContextMode).toHaveBeenCalledWith('file-1', 'persistent')
    expect(onRemoveFileContext).toHaveBeenCalledWith('file-1')
    expect(screen.getByText('Processing upload')).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: /sticky mode for draft\.pdf/i })).toBeDisabled()
  })

  it('renders pending images and allows removing them through inactive state', () => {
    const onRemovePendingImage = vi.fn()

    render(
      <ManageUploadsPanel
        isOpen={true}
        uploadedKnowledgeFiles={[]}
        pendingImages={[{ id: 'img-1', filename: 'chart.png' }]}
        onClose={vi.fn()}
        onRemoveFileContext={vi.fn()}
        onSetFileContextMode={vi.fn()}
        onRemovePendingImage={onRemovePendingImage}
      />,
    )

    expect(screen.getByText('Current Turn Images')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /mark chart\.png inactive/i }))
    expect(onRemovePendingImage).toHaveBeenCalledWith('img-1')
    expect(
      screen.getByRole('button', { name: /sticky mode is unavailable for chart\.png/i }),
    ).toBeDisabled()
  })
})
