import { type CSSProperties } from 'react'
import type { FileBindingMode } from '../hooks/useFileContext'
import {
  CloseIcon,
  DocumentIcon,
  ImageIcon,
  ProcessingDot,
  ReadyDot,
  modeLabel,
} from './chatComposerPrimitives'

interface UploadedKnowledgeFile {
  id: string
  filename: string
  status: 'ready' | 'processing'
  bindingMode: FileBindingMode
}

interface PendingImageAttachment {
  id: string
  filename: string
}

interface ManageUploadsPanelProps {
  isOpen: boolean
  uploadedKnowledgeFiles: UploadedKnowledgeFile[]
  pendingImages: PendingImageAttachment[]
  onClose: () => void
  onRemoveFileContext: (id: string) => void
  onSetFileContextMode: (id: string, mode: FileBindingMode) => void
  onRemovePendingImage: (id: string) => void
}

const panelStyle = {
  borderColor: 'var(--input-border)',
  background: 'var(--composer-menu-bg-strong)',
  backdropFilter: 'blur(18px)',
} satisfies CSSProperties

export default function ManageUploadsPanel({
  isOpen,
  uploadedKnowledgeFiles,
  pendingImages,
  onClose,
  onRemoveFileContext,
  onSetFileContextMode,
  onRemovePendingImage,
}: ManageUploadsPanelProps) {
  if (!isOpen) return null

  return (
    <div
      className="absolute bottom-14 left-0 z-30 w-[min(560px,calc(100vw-3rem))] rounded-3xl border p-4 shadow-[0_12px_24px_rgba(15,23,42,0.08)]"
      style={panelStyle}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold" style={{ color: 'var(--text-main)' }}>
            Manage Uploads
          </h3>
          <p className="mt-1 text-xs" style={{ color: 'var(--text-muted)' }}>
            Control which uploaded knowledge files flow into future turns.
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="flex h-8 w-8 items-center justify-center rounded-full transition-colors hover:bg-slate-900/[0.04]"
          style={{ color: 'var(--text-muted)' }}
          title="Close upload manager"
        >
          <CloseIcon />
        </button>
      </div>

      <div className="mt-4 max-h-[320px] space-y-3 overflow-y-auto pr-1">
        {uploadedKnowledgeFiles.length === 0 && pendingImages.length === 0 ? (
          <div
            className="rounded-2xl border px-4 py-6 text-center text-sm"
            style={{
              borderColor: 'var(--input-border)',
              background: 'var(--composer-muted-surface)',
              color: 'var(--text-muted)',
            }}
          >
            No uploaded files yet.
          </div>
        ) : (
          <>
            {uploadedKnowledgeFiles.map(file => (
              <div
                key={file.id}
                className="rounded-2xl border px-4 py-3"
                style={{
                  borderColor: 'var(--input-border)',
                  background: 'var(--composer-menu-bg)',
                }}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div
                      className="inline-flex items-center gap-2 text-sm font-medium"
                      style={{ color: 'var(--text-main)' }}
                    >
                      <DocumentIcon />
                      <span className="truncate">{file.filename}</span>
                    </div>
                    <div
                      className="mt-1 inline-flex items-center gap-2 text-xs"
                      style={{ color: 'var(--text-muted)' }}
                    >
                      {file.status === 'ready' ? <ReadyDot /> : <ProcessingDot />}
                      <span>
                        {file.status === 'ready'
                          ? `Mode: ${modeLabel(file.bindingMode)}`
                          : 'Processing upload'}
                      </span>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => onRemoveFileContext(file.id)}
                    className="rounded-full px-2.5 py-1 text-xs transition-colors hover:bg-slate-900/[0.04]"
                    style={{ color: 'var(--composer-danger-text)' }}
                  >
                    Delete
                  </button>
                </div>

                <div
                  className="mt-3 inline-flex overflow-hidden rounded-full border"
                  style={{
                    borderColor: 'var(--input-border)',
                    background: 'var(--composer-muted-surface)',
                  }}
                >
                  {([
                    ['single', 'Next Turn'],
                    ['persistent', 'Sticky'],
                    ['idle', 'Inactive'],
                  ] as Array<[FileBindingMode, string]>).map(([mode, label]) => (
                    <button
                      key={mode}
                      type="button"
                      disabled={file.status !== 'ready'}
                      onClick={() => onSetFileContextMode(file.id, mode)}
                      className="border-l px-3 py-1.5 text-[11px] font-medium transition-colors first:border-l-0 disabled:cursor-not-allowed disabled:opacity-50"
                      style={{
                        borderColor: 'rgba(15,23,42,0.08)',
                        background:
                          file.bindingMode === mode
                            ? 'var(--composer-selected-surface)'
                            : 'transparent',
                        color:
                          file.bindingMode === mode ? 'var(--text-main)' : 'var(--text-muted)',
                      }}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>
            ))}
            {pendingImages.length > 0 && (
              <div className="space-y-3">
                <p
                  className="px-1 text-[11px] font-medium uppercase tracking-[0.08em]"
                  style={{ color: 'var(--text-muted)' }}
                >
                  Current Turn Images
                </p>
                {pendingImages.map(image => (
                  <div
                    key={image.id}
                    className="rounded-2xl border px-4 py-3"
                    style={{
                      borderColor: 'var(--input-border)',
                      background: 'var(--composer-menu-bg)',
                    }}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div
                          className="inline-flex items-center gap-2 text-sm font-medium"
                          style={{ color: 'var(--text-main)' }}
                        >
                          <ImageIcon />
                          <span className="truncate">{image.filename}</span>
                        </div>
                        <p className="mt-1 text-xs" style={{ color: 'var(--text-muted)' }}>
                          Vision attachments stay on the next send only.
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() => onRemovePendingImage(image.id)}
                        className="rounded-full px-2.5 py-1 text-xs transition-colors hover:bg-slate-900/[0.04]"
                        style={{ color: 'var(--composer-danger-text)' }}
                      >
                        Delete
                      </button>
                    </div>
                    <div
                      className="mt-3 inline-flex overflow-hidden rounded-full border"
                      style={{
                        borderColor: 'var(--input-border)',
                        background: 'var(--composer-muted-surface)',
                      }}
                    >
                      <button
                        type="button"
                        className="px-3 py-1.5 text-[11px] font-medium"
                        style={{
                          background: 'var(--composer-selected-surface)',
                          color: 'var(--text-main)',
                        }}
                      >
                        Next Turn
                      </button>
                      <button
                        type="button"
                        disabled
                        className="border-l px-3 py-1.5 text-[11px] font-medium opacity-50"
                        style={{
                          borderColor: 'rgba(15,23,42,0.08)',
                          color: 'var(--text-muted)',
                        }}
                        title="Sticky mode is not available for image attachments yet"
                      >
                        Sticky
                      </button>
                      <button
                        type="button"
                        onClick={() => onRemovePendingImage(image.id)}
                        className="border-l px-3 py-1.5 text-[11px] font-medium transition-colors"
                        style={{
                          borderColor: 'rgba(15,23,42,0.08)',
                          color: 'var(--text-muted)',
                        }}
                      >
                        Inactive
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
