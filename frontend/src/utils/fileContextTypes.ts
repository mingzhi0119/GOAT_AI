export type FileBindingMode = 'idle' | 'single' | 'persistent'
export type FileUploadStatus = 'processing' | 'ready'

export interface FileContextItem {
  id: string
  filename: string
  documentId?: string
  ingestionId?: string
  retrievalMode?: string
  suffixPrompt?: string
  templatePrompt?: string
  bindingMode: FileBindingMode
  status: FileUploadStatus
}

export interface FileContextUpdate {
  id?: string
  filename: string
  documentId?: string
  ingestionId?: string
  retrievalMode?: string
  suffixPrompt?: string
  templatePrompt?: string
  bindingMode?: FileBindingMode
  status?: FileUploadStatus
}
