import { fetchApi } from './http'
import { buildApiUrl } from './urls'

function resolveDownloadFilename(
  contentDisposition: string | null,
  fallbackFilename: string,
): string {
  if (!contentDisposition) return fallbackFilename

  const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i)
  if (utf8Match?.[1]) {
    try {
      return decodeURIComponent(utf8Match[1])
    } catch {
      return utf8Match[1]
    }
  }

  const filenameMatch = contentDisposition.match(/filename="?([^";]+)"?/i)
  return filenameMatch?.[1]?.trim() || fallbackFilename
}

export async function downloadFile(
  downloadUrl: string,
  fallbackFilename: string,
): Promise<void> {
  const response = await fetchApi(buildApiUrl(downloadUrl), {
    method: 'GET',
  })

  if (!response.ok) {
    throw new Error(`Download failed with HTTP ${response.status}`)
  }

  const blob = await response.blob()
  const objectUrl = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = objectUrl
  anchor.download = resolveDownloadFilename(
    response.headers.get('Content-Disposition'),
    fallbackFilename,
  )
  anchor.style.display = 'none'
  document.body.appendChild(anchor)

  try {
    anchor.click()
  } finally {
    document.body.removeChild(anchor)
    setTimeout(() => URL.revokeObjectURL(objectUrl), 0)
  }
}
