import { useEffect, useState, type FC } from 'react'
import { brandingConfig } from '../config/branding'
import {
  CODE_FONT_OPTIONS,
  THEME_STYLES,
  UI_FONT_OPTIONS,
  getComputedThemeTokens,
  getStyleAccentPresets,
  formatColorTokenDisplay,
  type AppearanceConfig,
  type AppearanceMode,
  type AppearanceStyleId,
  type CodeFontId,
  type ResolvedThemeMode,
  type UIFontId,
} from '../utils/appearance'

interface Props {
  open: boolean
  appearance: AppearanceConfig
  effectiveMode: ResolvedThemeMode
  onClose: () => void
  onChange: (patch: Partial<AppearanceConfig>) => void
  onReset: () => void
}

const MODE_OPTIONS: Array<{ id: AppearanceMode; label: string; icon: string }> = [
  { id: 'light', label: 'Light', icon: '☀' },
  { id: 'dark', label: 'Dark', icon: '☾' },
  { id: 'system', label: 'System', icon: '◫' },
]

const AppearancePanel: FC<Props> = ({
  open,
  appearance,
  effectiveMode,
  onClose,
  onChange,
  onReset,
}) => {
  const [accentInput, setAccentInput] = useState(appearance.accentColor)

  useEffect(() => {
    if (!open) return
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [onClose, open])

  useEffect(() => {
    setAccentInput(appearance.accentColor)
  }, [appearance.accentColor])

  if (!open) return null

  const tokens = getComputedThemeTokens(appearance, effectiveMode === 'dark')
  const accentPresets = getStyleAccentPresets(appearance.themeStyle)

  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center bg-black/30 px-4 py-6 backdrop-blur-[2px]">
      <div
        aria-hidden="true"
        className="absolute inset-0"
        onMouseDown={onClose}
      />
      <section
        role="dialog"
        aria-modal="true"
        aria-label="Appearance settings"
        className="relative z-[81] flex max-h-[min(92vh,56rem)] w-[min(96vw,70rem)] flex-col overflow-hidden rounded-[32px] border shadow-[0_28px_80px_var(--panel-shadow-color)]"
        style={{
          background: 'var(--composer-menu-bg-strong)',
          borderColor: 'var(--input-border)',
          color: 'var(--text-main)',
        }}
      >
        <header
          className="flex items-start justify-between gap-4 border-b px-6 py-5"
          style={{ borderColor: 'var(--border-color)' }}
        >
          <div>
            <h2 className="text-[1.75rem] font-semibold tracking-[-0.03em]">Appearance</h2>
            <p className="mt-1 text-sm" style={{ color: 'var(--text-muted)' }}>
              Tune the shell, typography, and contrast of {brandingConfig.displayName}.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="rounded-full border px-3 py-1.5 text-sm transition-opacity hover:opacity-90"
              style={{
                borderColor: 'var(--border-color)',
                color: 'var(--text-main)',
                background: 'var(--composer-muted-surface)',
              }}
              onClick={onReset}
            >
              Reset defaults
            </button>
            <button
              type="button"
              aria-label="Close appearance panel"
              className="inline-flex h-10 w-10 items-center justify-center rounded-full transition-opacity hover:opacity-90"
              style={{
                background: 'var(--composer-muted-surface)',
                color: 'var(--text-main)',
              }}
              onClick={onClose}
            >
              ×
            </button>
          </div>
        </header>

        <div className="grid min-h-0 flex-1 gap-0 lg:grid-cols-[1.12fr_0.88fr]">
          <div className="min-h-0 overflow-y-auto px-6 py-5">
            <div className="space-y-5">
              <section
                className="rounded-[28px] border p-4"
                style={{ borderColor: 'var(--border-color)', background: 'var(--composer-menu-bg)' }}
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h3 className="text-base font-semibold">Theme mode</h3>
                    <p className="mt-1 text-sm" style={{ color: 'var(--text-muted)' }}>
                      Match system settings or lock the UI to a single mode.
                    </p>
                  </div>
                  <div
                    className="inline-flex rounded-full p-1"
                    style={{ background: 'var(--composer-muted-surface)' }}
                    role="radiogroup"
                    aria-label="Theme mode"
                  >
                    {MODE_OPTIONS.map(option => {
                      const selected = appearance.themeMode === option.id
                      return (
                        <button
                          key={option.id}
                          type="button"
                          role="radio"
                          aria-checked={selected}
                          className="inline-flex min-w-[6.5rem] items-center justify-center gap-2 rounded-full px-3 py-2 text-sm transition-all"
                          style={{
                            background: selected ? 'var(--theme-accent-soft)' : 'transparent',
                            color: selected ? 'var(--text-main)' : 'var(--text-muted)',
                          }}
                          onClick={() => onChange({ themeMode: option.id })}
                        >
                          <span aria-hidden="true">{option.icon}</span>
                          <span>{option.label}</span>
                        </button>
                      )
                    })}
                  </div>
                </div>
              </section>

              <section
                className="rounded-[28px] border p-4"
                style={{ borderColor: 'var(--border-color)', background: 'var(--composer-menu-bg)' }}
              >
                <h3 className="text-base font-semibold">Theme style</h3>
                <p className="mt-1 text-sm" style={{ color: 'var(--text-muted)' }}>
                  Choose a curated product skin with its own surface rhythm and tone.
                </p>
                <div className="mt-4 grid gap-3 md:grid-cols-3">
                  {THEME_STYLES.map(style => {
                    const selected = appearance.themeStyle === style.id
                    const previewTokens = style.tokens[effectiveMode]
                    return (
                      <button
                        key={style.id}
                        type="button"
                        className="rounded-[24px] border p-3 text-left transition-transform hover:-translate-y-0.5"
                        style={{
                          borderColor: selected ? 'var(--theme-accent)' : 'var(--border-color)',
                          background: selected ? 'var(--theme-accent-soft)' : 'var(--composer-muted-surface)',
                        }}
                        onClick={() =>
                          onChange({
                            themeStyle: style.id,
                            accentColor: style.accentPresets[0] ?? appearance.accentColor,
                          })
                        }
                      >
                        <div
                          className="h-20 rounded-[18px] border p-3"
                          style={{
                            borderColor: previewTokens.borderColor,
                            background: previewTokens.chatBg,
                          }}
                        >
                          <div className="flex h-full gap-2">
                            <div
                              className="w-[32%] rounded-[12px]"
                              style={{ background: previewTokens.sidebarBg }}
                            />
                            <div className="flex-1 space-y-2 rounded-[12px]">
                              <div
                                className="h-5 rounded-full"
                                style={{ background: previewTokens.assistantBubbleBg }}
                              />
                              <div
                                className="h-8 rounded-[14px]"
                                style={{ background: style.accentPresets[0] }}
                              />
                            </div>
                          </div>
                        </div>
                        <div className="mt-3 flex min-h-[8.75rem] flex-col justify-start">
                          <div className="relative min-h-[1.5rem] pr-16">
                            <p className="text-sm font-semibold">{style.label}</p>
                            {selected && (
                              <span
                                className="absolute right-0 top-0 rounded-full px-2 py-1 text-[11px] font-semibold leading-none"
                                style={{
                                  background: 'var(--theme-accent)',
                                  color: 'var(--theme-accent-contrast)',
                                }}
                              >
                                Active
                              </span>
                            )}
                          </div>
                          <p
                            className="mt-1 text-xs leading-5"
                            style={{ color: 'var(--text-muted)' }}
                          >
                            {style.description}
                          </p>
                        </div>
                      </button>
                    )
                  })}
                </div>
              </section>

              <section
                className="rounded-[28px] border p-4"
                style={{ borderColor: 'var(--border-color)', background: 'var(--composer-menu-bg)' }}
              >
                <h3 className="text-base font-semibold">Accent</h3>
                <p className="mt-1 text-sm" style={{ color: 'var(--text-muted)' }}>
                  Accent drives selections, send actions, highlights, and links.
                </p>
                <div className="mt-4 flex flex-wrap gap-2">
                  {accentPresets.map(color => {
                    const selected = appearance.accentColor === color
                    return (
                      <button
                        key={color}
                        type="button"
                        aria-label={`Accent ${color}`}
                        className="h-10 w-10 rounded-full border-2 transition-transform hover:scale-[1.04]"
                        style={{
                          background: color,
                          borderColor: selected ? 'var(--text-main)' : 'transparent',
                          boxShadow: selected ? '0 0 0 3px var(--composer-menu-bg-strong)' : 'none',
                        }}
                        onClick={() => onChange({ accentColor: color })}
                      />
                    )
                  })}
                </div>
                <div className="mt-4 grid gap-3 sm:grid-cols-[auto_1fr] sm:items-center">
                  <label className="text-sm font-medium" htmlFor="appearance-accent-input">
                    Custom accent
                  </label>
                  <div className="flex items-center gap-3">
                    <input
                      id="appearance-accent-picker"
                      type="color"
                      aria-label="Accent color picker"
                      value={appearance.accentColor}
                      onChange={event => onChange({ accentColor: event.target.value })}
                      className="h-10 w-14 cursor-pointer rounded-xl border bg-transparent p-1"
                      style={{ borderColor: 'var(--border-color)' }}
                    />
                    <input
                      id="appearance-accent-input"
                      type="text"
                      value={accentInput}
                      onChange={event => setAccentInput(event.target.value)}
                      onBlur={() => {
                        const normalized = accentInput.startsWith('#')
                          ? accentInput
                          : `#${accentInput}`
                        if (/^#[0-9a-f]{6}$/i.test(normalized)) {
                          onChange({ accentColor: normalized.toLowerCase() })
                        } else {
                          setAccentInput(appearance.accentColor)
                        }
                      }}
                      className="w-full rounded-2xl border px-3 py-2 text-sm focus:outline-none focus:ring-2"
                      style={{
                        borderColor: 'var(--input-border)',
                        background: 'var(--input-bg)',
                        color: 'var(--text-main)',
                      }}
                    />
                  </div>
                </div>
                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  <ColorReadout label="Background" value={tokens.mainBg} />
                  <ColorReadout label="Foreground" value={tokens.textMain} />
                </div>
              </section>

              <section
                className="rounded-[28px] border p-4"
                style={{ borderColor: 'var(--border-color)', background: 'var(--composer-menu-bg)' }}
              >
                <h3 className="text-base font-semibold">Typography</h3>
                <div className="mt-4 grid gap-4 sm:grid-cols-2">
                  <FontSelect
                    label="UI font"
                    value={appearance.uiFont}
                    options={UI_FONT_OPTIONS}
                    onChange={value => onChange({ uiFont: value as UIFontId })}
                  />
                  <FontSelect
                    label="Code font"
                    value={appearance.codeFont}
                    options={CODE_FONT_OPTIONS}
                    onChange={value => onChange({ codeFont: value as CodeFontId })}
                  />
                </div>
              </section>

              <section
                className="rounded-[28px] border p-4"
                style={{ borderColor: 'var(--border-color)', background: 'var(--composer-menu-bg)' }}
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h3 className="text-base font-semibold">Contrast</h3>
                    <p className="mt-1 text-sm" style={{ color: 'var(--text-muted)' }}>
                      Increase edge definition and muted-text separation.
                    </p>
                  </div>
                  <span className="text-sm font-medium">{appearance.contrast}</span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={100}
                  step={1}
                  aria-label="Contrast"
                  value={appearance.contrast}
                  onChange={event => onChange({ contrast: Number.parseInt(event.target.value, 10) })}
                  className="appearance-contrast-slider mt-4 w-full accent-[var(--theme-accent)]"
                  style={{ cursor: 'ew-resize' }}
                />
              </section>

              <section
                className="rounded-[28px] border p-4"
                style={{ borderColor: 'var(--border-color)', background: 'var(--composer-menu-bg)' }}
              >
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <h3 className="text-base font-semibold">Translucent sidebar</h3>
                    <p className="mt-1 text-sm" style={{ color: 'var(--text-muted)' }}>
                      Use a softer glass treatment for sidebar surfaces and menu chrome.
                    </p>
                  </div>
                  <button
                    type="button"
                    role="switch"
                    aria-checked={appearance.translucentSidebar}
                    aria-label="Translucent sidebar"
                    className="relative inline-flex h-8 w-14 items-center rounded-full transition-colors"
                    style={{
                      background: appearance.translucentSidebar
                        ? 'var(--theme-accent)'
                        : 'var(--composer-selected-surface)',
                    }}
                    onClick={() =>
                      onChange({ translucentSidebar: !appearance.translucentSidebar })
                    }
                  >
                    <span
                      className="inline-block h-6 w-6 rounded-full bg-white transition-transform"
                      style={{
                        transform: appearance.translucentSidebar
                          ? 'translateX(30px)'
                          : 'translateX(4px)',
                      }}
                    />
                  </button>
                </div>
              </section>
            </div>
          </div>

          <aside
            className="min-h-0 overflow-y-auto border-l px-6 py-5"
            style={{ borderColor: 'var(--border-color)', background: 'var(--composer-muted-surface)' }}
          >
            <div className="sticky top-0 space-y-4">
              <div>
                <h3 className="text-base font-semibold">Live preview</h3>
                <p className="mt-1 text-sm" style={{ color: 'var(--text-muted)' }}>
                  The preview reflects the exact appearance state currently applied to the app.
                </p>
              </div>

              <div
                className="overflow-hidden rounded-[28px] border"
                style={{ borderColor: tokens.borderColor, background: tokens.chatBg }}
              >
                <div
                  className="flex items-center justify-between border-b px-4 py-3"
                  style={{ borderColor: tokens.borderColor, background: tokens.panelBgStrong }}
                >
                  <div>
                    <p className="text-sm font-semibold" style={{ color: tokens.textMain }}>
                      {brandingConfig.displayName} shell
                    </p>
                    <p className="text-xs" style={{ color: tokens.textMuted }}>
                      {appearance.themeStyle} · {appearance.themeMode} · {effectiveMode}
                    </p>
                  </div>
                  <span
                    className="rounded-full px-2 py-1 text-[11px] font-semibold"
                    style={{
                      background: appearance.accentColor,
                      color: 'var(--theme-accent-contrast)',
                    }}
                  >
                    Accent
                  </span>
                </div>
                <div className="flex h-[24rem]">
                  <div
                    className="w-[34%] border-r px-3 py-4"
                    style={{
                      borderColor: tokens.borderColor,
                      background: tokens.sidebarBg,
                      backdropFilter: appearance.translucentSidebar ? 'blur(18px)' : 'none',
                    }}
                  >
                    <div
                      className="rounded-[18px] px-3 py-2"
                      style={{ background: tokens.sidebarSurface, color: tokens.textSidebar }}
                    >
                      New chat
                    </div>
                    <div className="mt-3 space-y-2">
                      <PreviewListItem
                        title="Strategy review"
                        subtitle="Last updated 3m ago"
                        background={tokens.sidebarSurfaceMuted}
                        titleColor={tokens.textSidebar}
                        subtitleColor={tokens.sidebarMuted}
                      />
                      <PreviewListItem
                        title="Leadership memo"
                        subtitle="Pinned"
                        background={tokens.sidebarSurfaceMuted}
                        titleColor={tokens.textSidebar}
                        subtitleColor={tokens.sidebarMuted}
                      />
                    </div>
                  </div>
                  <div className="flex-1 px-4 py-4" style={{ background: tokens.chatBg }}>
                    <div className="space-y-3">
                      <div
                        className="max-w-[82%] rounded-[22px] px-4 py-3"
                        style={{
                          background: tokens.assistantBubbleBg,
                          color: tokens.textAssistantBubble,
                          border: `1px solid ${tokens.borderColor}`,
                        }}
                      >
                        Revenue mix looks stable, but margin pressure is rising in the northeast
                        segment.
                      </div>
                      <div
                        className="ml-auto max-w-[74%] rounded-[22px] px-4 py-3"
                        style={{
                          background: appearance.accentColor,
                          color: 'var(--theme-accent-contrast)',
                        }}
                      >
                        Pull the chart and show the sharpest quarter-over-quarter change.
                      </div>
                      <div
                        className="rounded-[24px] border p-3"
                        style={{
                          borderColor: tokens.inputBorder,
                          background: tokens.panelBgStrong,
                        }}
                      >
                        <div
                          className="grid grid-cols-2 overflow-hidden rounded-[18px] border text-sm"
                          style={{
                            borderColor: tokens.borderColor,
                            fontFamily: 'var(--code-font-family)',
                          }}
                        >
                          <div className="space-y-1 border-r p-3" style={{ borderColor: tokens.borderColor, background: tokens.previewDiffRemoved }}>
                            <p style={{ color: tokens.previewCodeA }}>const</p>
                            <p style={{ color: tokens.previewCodeB }}>accent: oldTone</p>
                            <p style={{ color: tokens.textMuted }}>contrast: 32</p>
                          </div>
                          <div className="space-y-1 p-3" style={{ background: tokens.previewDiffAdded }}>
                            <p style={{ color: tokens.previewCodeA }}>const</p>
                            <p style={{ color: tokens.previewCodeB }}>accent: refinedTone</p>
                            <p style={{ color: tokens.textMuted }}>contrast: {appearance.contrast}</p>
                          </div>
                        </div>
                        <div
                          className="mt-3 rounded-[18px] px-3 py-2 text-sm"
                          style={{
                            background: tokens.codeBlockBg,
                            color: '#e5edf8',
                            fontFamily: 'var(--code-font-family)',
                          }}
                        >
                          themeMode: "{appearance.themeMode}"
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <MetricCard label="Panel surface" value={tokens.panelBgStrong} />
                <MetricCard label="Link tone" value={tokens.linkColor} />
              </div>
            </div>
          </aside>
        </div>
      </section>
    </div>
  )
}

interface FontSelectProps {
  label: string
  value: string
  options: Array<{ id: string; label: string; cssValue: string }>
  onChange: (value: string) => void
}

function FontSelect({ label, value, options, onChange }: FontSelectProps) {
  return (
    <label className="block">
      <span className="mb-2 block text-sm font-medium">{label}</span>
      <select
        value={value}
        onChange={event => onChange(event.target.value)}
        className="w-full rounded-2xl border px-3 py-2.5 text-sm focus:outline-none focus:ring-2"
        style={{
          borderColor: 'var(--input-border)',
          background: 'var(--input-bg)',
          color: 'var(--text-main)',
        }}
      >
        {options.map(option => (
          <option key={option.id} value={option.id} style={{ fontFamily: option.cssValue }}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  )
}

function ColorReadout({ label, value }: { label: string; value: string }) {
  const displayValue = formatColorTokenDisplay(value)
  return (
    <div
      className="rounded-[22px] border px-4 py-3"
      style={{ borderColor: 'var(--border-color)', background: 'var(--composer-muted-surface)' }}
    >
      <p className="text-xs font-semibold uppercase tracking-[0.08em]" style={{ color: 'var(--text-muted)' }}>
        {label}
      </p>
      <div className="mt-2 flex items-center gap-3">
        <span
          className="inline-block h-8 w-8 rounded-full border"
          style={{ background: value, borderColor: 'var(--border-color)' }}
        />
        <code style={{ fontFamily: 'var(--code-font-family)' }}>{displayValue}</code>
      </div>
    </div>
  )
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div
      className="rounded-[24px] border px-4 py-3"
      style={{ borderColor: 'var(--border-color)', background: 'var(--composer-menu-bg)' }}
    >
      <p className="text-xs font-semibold uppercase tracking-[0.08em]" style={{ color: 'var(--text-muted)' }}>
        {label}
      </p>
      <p className="mt-2 text-sm font-medium" style={{ fontFamily: 'var(--code-font-family)' }}>
        {formatColorTokenDisplay(value)}
      </p>
    </div>
  )
}

function PreviewListItem({
  title,
  subtitle,
  background,
  titleColor,
  subtitleColor,
}: {
  title: string
  subtitle: string
  background: string
  titleColor: string
  subtitleColor: string
}) {
  return (
    <div className="rounded-[16px] px-3 py-2" style={{ background }}>
      <p className="truncate text-sm font-medium" style={{ color: titleColor }}>
        {title}
      </p>
      <p className="mt-1 truncate text-xs" style={{ color: subtitleColor }}>
        {subtitle}
      </p>
    </div>
  )
}

export default AppearancePanel
