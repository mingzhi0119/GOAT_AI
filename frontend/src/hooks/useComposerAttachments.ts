import { useCallback, useMemo, useState, type ChangeEvent } from 'react'
import { uploadMediaImage } from '../api/media'
import { streamUpload, type UploadStreamEvent } from '../api/upload'

export interface PendingImageAttachment {
  id: string
  filename: string
}

interface UseComposerAttachmentsArgs {
  supportsVision: boolean
  onUploadEvent: (event: UploadStreamEvent) => void
}

interface UseComposerAttachmentsReturn {
  attachmentAccept: string
  attachmentUploadError: string | null
  attachmentUploading: boolean
  pendingImages: PendingImageAttachment[]
  clearPendingImages: () => void
  handleAttachmentPick: (event: ChangeEvent<HTMLInputElement>) => Promise<void>
  removePendingImage: (id: string) => void
}

const KNOWLEDGE_FILE_EXTENSIONS = new Set(['csv', 'xlsx', 'pdf', 'docx', 'md', 'txt'])
const IMAGE_FILE_EXTENSIONS = new Set(['png', 'jpg', 'jpeg', 'webp'])

function getFileExtension(filename: string): string {
  const lastDot = filename.lastIndexOf('.')
  if (lastDot < 0) return ''
  return filename.slice(lastDot + 1).toLowerCase()
}

function getAttachmentKind(file: File, supportsVision: boolean): 'image' | 'knowledge' | 'unsupported' {
  const ext = getFileExtension(file.name)
  if (KNOWLEDGE_FILE_EXTENSIONS.has(ext)) return 'knowledge'
  if (supportsVision && IMAGE_FILE_EXTENSIONS.has(ext)) return 'image'
  return 'unsupported'
}

function supportedAttachmentLabel(supportsVision: boolean): string {
  return supportsVision
    ? 'PNG, JPG, WEBP, CSV, XLSX, PDF, DOCX, MD, or TXT'
    : 'CSV, XLSX, PDF, DOCX, MD, or TXT'
}

function formatAttachmentErrorMessage(error: unknown, supportsVision: boolean): string {
  const fallback = 'Attachment upload failed'
  const message = error instanceof Error ? error.message : fallback
  if (message.startsWith('Unsupported file type:')) {
    return `Unsupported file type. Please upload a ${supportedAttachmentLabel(supportsVision)} file.`
  }
  return message
}

async function uploadKnowledgeFile(
  file: File,
  onUploadEvent: (event: UploadStreamEvent) => void,
): Promise<void> {
  for await (const event of streamUpload(file)) {
    if (event.type === 'file_prompt' || event.type === 'knowledge_ready') {
      onUploadEvent(event)
    } else if (event.type === 'error') {
      throw new Error(event.message)
    }
  }
}

export function useComposerAttachments({
  supportsVision,
  onUploadEvent,
}: UseComposerAttachmentsArgs): UseComposerAttachmentsReturn {
  const [pendingImages, setPendingImages] = useState<PendingImageAttachment[]>([])
  const [attachmentUploadError, setAttachmentUploadError] = useState<string | null>(null)
  const [attachmentUploading, setAttachmentUploading] = useState(false)

  const attachmentAccept = useMemo(
    () =>
      supportsVision
        ? 'image/png,image/jpeg,image/jpg,image/webp,.csv,.xlsx,.pdf,.docx,.md,.txt'
        : '.csv,.xlsx,.pdf,.docx,.md,.txt',
    [supportsVision],
  )

  const clearPendingImages = useCallback(() => {
    setPendingImages([])
    setAttachmentUploadError(null)
  }, [])

  const removePendingImage = useCallback((id: string) => {
    setPendingImages(prev => prev.filter(item => item.id !== id))
  }, [])

  const handleAttachmentPick = useCallback(
    async (event: ChangeEvent<HTMLInputElement>) => {
      const files = event.target.files ? Array.from(event.target.files) : []
      event.target.value = ''
      if (files.length === 0) return

      setAttachmentUploadError(null)
      setAttachmentUploading(true)
      try {
        const knowledgeFiles = files.filter(
          file => getAttachmentKind(file, supportsVision) === 'knowledge',
        )
        const imageFiles = files.filter(file => getAttachmentKind(file, supportsVision) === 'image')
        const unsupportedFiles = files.filter(
          file => getAttachmentKind(file, supportsVision) === 'unsupported',
        )

        if (unsupportedFiles.length > 0) {
          throw new Error(`Unsupported file type: ${unsupportedFiles[0]!.name}`)
        }
        if (knowledgeFiles.length > 1) {
          throw new Error('Please upload one knowledge file at a time.')
        }

        for (const imageFile of imageFiles) {
          const result = await uploadMediaImage(imageFile)
          setPendingImages(prev => [...prev, { id: result.attachment_id, filename: imageFile.name }])
        }

        const knowledgeFile = knowledgeFiles[0]
        if (knowledgeFile) {
          await uploadKnowledgeFile(knowledgeFile, onUploadEvent)
        }
      } catch (error) {
        setAttachmentUploadError(formatAttachmentErrorMessage(error, supportsVision))
      } finally {
        setAttachmentUploading(false)
      }
    },
    [onUploadEvent, supportsVision],
  )

  return {
    attachmentAccept,
    attachmentUploadError,
    attachmentUploading,
    pendingImages,
    clearPendingImages,
    handleAttachmentPick,
    removePendingImage,
  }
}
