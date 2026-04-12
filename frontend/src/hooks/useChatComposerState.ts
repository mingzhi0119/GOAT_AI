import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type KeyboardEvent as ReactKeyboardEvent,
  type RefObject,
} from 'react'

const TEXTAREA_MAX_HEIGHT_PX = 144
const TEXTAREA_MIN_HEIGHT_PX = 28
const DEFAULT_IMAGE_PROMPT = 'What do you see in this image?'

interface UseChatComposerStateArgs {
  isStreaming: boolean
  attachmentUploading: boolean
  pendingImageIds: string[]
  onSendMessage: (content: string, imageAttachmentIds?: string[]) => void
  clearPendingImages: () => void
  closeActivePanel: () => void
}

interface UseChatComposerStateReturn {
  input: string
  textareaRef: RefObject<HTMLTextAreaElement | null>
  canSend: boolean
  setInput: (value: string) => void
  handleSubmit: () => void
  handleComposerKeyDown: (event: ReactKeyboardEvent<HTMLTextAreaElement>) => void
}

export function useChatComposerState({
  isStreaming,
  attachmentUploading,
  pendingImageIds,
  onSendMessage,
  clearPendingImages,
  closeActivePanel,
}: UseChatComposerStateArgs): UseChatComposerStateReturn {
  const [input, setInput] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    const textarea = textareaRef.current
    if (!textarea) return
    textarea.style.height = 'auto'
    const hasContent = input.trim().length > 0
    const nextHeight = hasContent
      ? Math.min(textarea.scrollHeight, TEXTAREA_MAX_HEIGHT_PX)
      : TEXTAREA_MIN_HEIGHT_PX
    textarea.style.height = `${Math.max(TEXTAREA_MIN_HEIGHT_PX, nextHeight)}px`
    textarea.style.overflowY = textarea.scrollHeight > TEXTAREA_MAX_HEIGHT_PX ? 'auto' : 'hidden'
  }, [input])

  const handleSubmit = useCallback(() => {
    const trimmed = input.trim()
    if ((!trimmed && pendingImageIds.length === 0) || isStreaming || attachmentUploading) return

    const text = trimmed || DEFAULT_IMAGE_PROMPT
    onSendMessage(text, pendingImageIds.length > 0 ? pendingImageIds : undefined)
    setInput('')
    clearPendingImages()
    closeActivePanel()
  }, [
    attachmentUploading,
    clearPendingImages,
    closeActivePanel,
    input,
    isStreaming,
    onSendMessage,
    pendingImageIds,
  ])

  const handleComposerKeyDown = useCallback(
    (event: ReactKeyboardEvent<HTMLTextAreaElement>) => {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault()
        handleSubmit()
      }
    },
    [handleSubmit],
  )

  return {
    input,
    textareaRef,
    canSend:
      (input.trim().length > 0 || pendingImageIds.length > 0) &&
      !isStreaming &&
      !attachmentUploading,
    setInput,
    handleSubmit,
    handleComposerKeyDown,
  }
}
