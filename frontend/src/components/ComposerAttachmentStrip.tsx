import type { PendingImageAttachment } from '../hooks/useComposerAttachments'
import type { FileContextItem } from '../hooks/useFileContext'
import {
  DocumentIcon,
  ImageIcon,
  ProcessingDot,
} from './chatComposerPrimitives'

interface ComposerAttachmentStripProps {
  uploadedKnowledgeFiles: FileContextItem[]
  pendingImages: PendingImageAttachment[]
}

export default function ComposerAttachmentStrip({
  uploadedKnowledgeFiles,
  pendingImages,
}: ComposerAttachmentStripProps) {
  const hasVisibleAttachments =
    uploadedKnowledgeFiles.length > 0 || pendingImages.length > 0

  if (!hasVisibleAttachments) {
    return null
  }

  return (
    <div
      className="ui-static flex flex-wrap items-center gap-2 px-1 pt-1"
      style={{ userSelect: 'none' }}
      aria-label="Current file and image attachments"
    >
      {uploadedKnowledgeFiles.map(file => (
        <div
          key={file.id}
          className="inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium"
          style={{
            borderColor: 'var(--composer-chip-border)',
            background: 'transparent',
            color: file.status === 'ready' ? 'var(--text-main)' : 'var(--text-muted)',
          }}
        >
          {file.status === 'ready' ? <DocumentIcon /> : <ProcessingDot />}
          <span className="max-w-[180px] truncate">{file.filename}</span>
        </div>
      ))}
      {pendingImages.map(image => (
        <div
          key={image.id}
          className="inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium"
          style={{
            borderColor: 'var(--composer-chip-border)',
            background: 'transparent',
            color: 'var(--text-main)',
          }}
        >
          <ImageIcon />
          <span className="max-w-[180px] truncate">{image.filename}</span>
        </div>
      ))}
    </div>
  )
}
