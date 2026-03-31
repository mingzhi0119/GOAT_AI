import { useCallback, useRef, useState, type DragEvent, type FC } from 'react'
import {
  streamUpload,
  type UploadChartSpecEvent,
  type UploadFileContextEvent,
} from '../api/upload'
import type { OllamaOptionsPayload } from '../api/types'

interface Props {
  model: string
  systemInstruction?: string
  getOllamaOptions: () => OllamaOptionsPayload
  onStream: (gen: AsyncGenerator<string>) => Promise<void>
  onFileContext: (ctx: UploadFileContextEvent) => void
  onChartSpec: (event: UploadChartSpecEvent) => void
}

/** Drag-and-drop / click-to-browse upload area for CSV and XLSX files. */
const FileUpload: FC<Props> = ({
  model,
  systemInstruction = '',
  getOllamaOptions,
  onStream,
  onFileContext,
  onChartSpec,
}) => {
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
        const source = streamUpload(file, model, systemInstruction, getOllamaOptions())
        async function* tokenOnly(): AsyncGenerator<string> {
          for await (const event of source) {
            if (typeof event === 'string') {
              yield event
            } else if (event.type === 'file_context') {
              onFileContext(event)
            } else if (event.type === 'chart_spec') {
              onChartSpec(event)
            }
          }
        }
        await onStream(tokenOnly())
        setStatus('done')
      } catch (err) {
        setErrorMsg(err instanceof Error ? err.message : 'Upload failed')
        setStatus('error')
      }
    },
    [model, onChartSpec, onFileContext, onStream, systemInstruction, getOllamaOptions],
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
      // Reset so the same file can be re-uploaded
      e.target.value = ''
    },
    [processFile],
  )

  const label =
    status === 'uploading'
      ? `Analyzing ${fileName ?? 'file'}…`
      : status === 'done'
        ? `${fileName ?? 'File'} ✓`
        : status === 'error'
          ? 'Upload failed — retry'
          : 'Drop CSV / XLSX\nor click to browse'

  return (
    <div>
      <div
        role="button"
        tabIndex={0}
        aria-label="Upload CSV or XLSX file"
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
        accept=".csv,.xlsx"
        className="hidden"
        onChange={handleChange}
      />
    </div>
  )
}

export default FileUpload
