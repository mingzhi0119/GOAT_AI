import { clearStoredProtectedAccess } from '../api/auth'
import { clearStoredChatState } from './chatLocalPersistence'
import { clearStoredFileContext } from './useFileContext'
import { clearStoredSystemInstruction } from './useSystemInstruction'
import { clearStoredUserName } from './useUserName'

export function clearBrowserPrivateState(): void {
  clearStoredChatState()
  clearStoredFileContext()
  clearStoredProtectedAccess()
  clearStoredUserName()
  clearStoredSystemInstruction()
}
