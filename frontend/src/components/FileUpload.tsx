import { useCallback, useRef, useState, type DragEvent, type FC } from 'react'
import {
  streamUpload,
  type UploadKnowledgeReadyEvent,
} from '../api/upload'

interface Props {
  onFileContext: (ctx: UploadKnowledgeReadyEvent) => void
}

/**
 * Drag-and-drop / click-to-browse upload area for supported knowledge files.
 *
 * On upload the backend ingests the file into the knowledge index and returns a
 * readiness event. The next chat turn then uses retrieval against that indexed
 * document.
 */
const FileUpload: FC<Props> = ({ onFileContext }) => {
  const [isDragging, setIsDragging] = useState(false)
  const [status, setStatus] = useState<'idle' | 'uploading' | 'done' | 'error'>('idle')
  const [fileName, setFileName] = useState<string | null>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const processFile = useCallback(
    async (file: File) => {
      setFileName(file.name)
      setErrorMsg(null)
      setStatus('uploading')
      try {
        for await (const event of streamUpload(file)) {
          if (event.type === 'knowledge_ready') onFileContext(event)
          else if (event.type === 'error') throw new Error(event.message)
        }
        setStatus('done')
      } catch (err) {
        setErrorMsg(err instanceof Error ? err.message : 'Upload failed')
        setStatus('error')
      }
    },
    [onFileContext],
  )

  const handleDrop = useCallback(
    (e: DragEvent<HTMLDivElement>) => {
      e.preventDefault()
      setIsDragging(false)
      const file = e.dataTransfer.files[0]
      if (file) void processFile(file)
    },
    [processFile],
  )

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0]
      if (file) void processFile(file)
      e.target.value = ''
    },
    [processFile],
  )

  const label =
    status === 'uploading'
      ? `Reading ${fileName ?? 'file'}…`
      : status === 'done'
        ? `${fileName ?? 'File'} ready ✓\nAsk your question below`
        : status === 'error'
          ? 'Upload failed — retry'
      : 'Drop CSV / XLSX / PDF / DOCX / MD\nor click to browse'

  return (
    <div>
      <div
        role="button"
        tabIndex={0}
        aria-label="Upload knowledge file"
        onClick={() => inputRef.current?.click()}
        onKeyDown={e => {
          if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click()
        }}
        onDragOver={e => {
          e.preventDefault()
          setIsDragging(true)
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        className="border-2 border-dashed rounded-xl p-3 text-center cursor-pointer transition-all text-xs leading-relaxed select-none"
        style={{
          borderColor: isDragging ? 'var(--gold)' : 'rgba(255,255,255,0.25)',
          background: isDragging ? 'rgba(255,205,0,0.08)' : 'rgba(255,255,255,0.04)',
          color: 'var(--text-sidebar)',
          opacity: status === 'uploading' ? 0.7 : 1,
        }}
      >
        <span className="whitespace-pre-line">{label}</span>
      </div>

      {errorMsg && (
        <p className="text-xs mt-1" style={{ color: '#f87171' }}>
          {errorMsg}
        </p>
      )}

      <input
        ref={inputRef}
        type="file"
        accept=".csv,.xlsx,.pdf,.docx,.md,.txt"
        className="hidden"
        onChange={handleChange}
      />
    </div>
  )
}

export default FileUpload
