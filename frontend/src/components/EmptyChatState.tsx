import type { ChatLayoutDecisions } from '../utils/chatLayout'

export interface EmptyChatPrompt {
  text: string
  kind: 'base' | 'suffix' | 'template'
}

interface EmptyChatStateProps {
  starterPrompts: EmptyChatPrompt[]
  selectedModel: string
  supportsVision: boolean
  layoutDecisions: ChatLayoutDecisions
  onSendMessage: (content: string) => void
}

export default function EmptyChatState({
  starterPrompts,
  selectedModel,
  supportsVision,
  layoutDecisions,
  onSendMessage,
}: EmptyChatStateProps) {
  return (
    <div
      className={`flex h-full flex-col items-center justify-center text-center ${layoutDecisions.compactSpacing ? 'gap-4 px-3' : 'gap-5 px-4'}`}
    >
      <div
        className="h-20 w-20 overflow-hidden rounded-2xl"
        style={{
          border: '1.5px solid #FFCD00',
          background: '#2b2b2b',
        }}
      >
        <img
          src="./golden_goat_icon.png"
          alt="GOAT AI"
          style={{ width: '100%', height: '100%', objectFit: 'cover' }}
        />
      </div>
      <div>
        <h2 className="mb-1 text-xl font-bold" style={{ color: 'var(--text-main)' }}>
          Welcome to GOAT AI
        </h2>
        <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
          Strategic Intelligence - Simon Business School
        </p>
        {selectedModel && (
          <p className="mt-1 text-xs" style={{ color: 'var(--text-muted)' }}>
            Model: <span style={{ color: 'var(--gold)' }}>{selectedModel}</span>
            {supportsVision && (
              <span className="ml-2" title="This model reports vision support in Ollama">
                vision
              </span>
            )}
          </p>
        )}
      </div>
      <div
        className={`mt-2 grid w-full max-w-md gap-2 ${layoutDecisions.singleColumnPrompts ? 'grid-cols-1' : 'grid-cols-2'}`}
      >
        {starterPrompts.map((item, index) => {
          const isFilePrompt = item.kind !== 'base'
          return (
            <button
              key={`${item.kind}-${index}-${item.text}`}
              onClick={() => onSendMessage(item.text)}
              className="rounded-xl px-3 py-2 text-left text-xs transition-colors hover:opacity-80"
              style={{
                border: isFilePrompt ? '1px solid var(--gold)' : '1px solid var(--border-color)',
                color: 'var(--text-main)',
                background: isFilePrompt ? 'rgba(255,205,0,0.08)' : 'var(--bg-asst-bubble)',
              }}
            >
              {isFilePrompt && (
                <span
                  className="mb-0.5 block text-[10px] font-semibold leading-none"
                  style={{ color: 'var(--gold)' }}
                >
                  {item.kind === 'suffix' ? 'From your file' : 'Template suggestion'}
                </span>
              )}
              {item.text}
            </button>
          )
        })}
      </div>
    </div>
  )
}
