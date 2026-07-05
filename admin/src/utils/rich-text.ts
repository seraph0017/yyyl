import DOMPurify from 'dompurify'

export type RichTextFormatCommand =
  | 'bold'
  | 'italic'
  | 'heading'
  | 'fontSize'
  | 'textColor'
  | 'backgroundColor'
  | 'divider'
  | 'image'
  | 'link'

export function sanitizeRichText(html: string | null | undefined): string {
  return DOMPurify.sanitize(html || '', {
    ADD_ATTR: ['target'],
    FORBID_TAGS: ['script', 'style'],
  })
}

function getSelectedHtml(): string {
  const selection = window.getSelection()
  if (!selection || selection.rangeCount === 0) return ''
  const range = selection.getRangeAt(0)
  const container = document.createElement('div')
  container.appendChild(range.cloneContents())
  return container.innerHTML || selection.toString()
}

function insertHtml(html: string) {
  document.execCommand('insertHTML', false, html)
}

function escapeAttribute(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

function normalizeLink(value: string): string {
  const link = value.trim()
  if (!link) return ''
  if (/^(https?:\/\/|\/|#)/i.test(link)) return link
  return `https://${link}`
}

export function applyRichTextCommand(command: RichTextFormatCommand, value?: string) {
  const selectedHtml = getSelectedHtml()
  const safeValue = value?.trim() || ''
  if (command === 'bold') {
    document.execCommand('bold')
    return
  }
  if (command === 'italic') {
    document.execCommand('italic')
    return
  }
  if (command === 'heading') {
    insertHtml(`<h3>${selectedHtml || '小标题'}</h3>`)
    return
  }
  if (command === 'fontSize') {
    const size = safeValue || '16px'
    insertHtml(`<span style="font-size: ${escapeAttribute(size)};">${selectedHtml || '文字'}</span>`)
    return
  }
  if (command === 'textColor') {
    const color = safeValue || '#2d4a3e'
    insertHtml(`<span style="color: ${escapeAttribute(color)};">${selectedHtml || '文字'}</span>`)
    return
  }
  if (command === 'backgroundColor') {
    const color = safeValue || '#faf6f0'
    insertHtml(`<span style="background-color: ${escapeAttribute(color)};">${selectedHtml || '文字'}</span>`)
    return
  }
  if (command === 'divider') {
    insertHtml('<hr />')
    return
  }
  if (command === 'image') {
    const url = safeValue
    if (!url) return
    insertHtml(`<img src="${escapeAttribute(url)}" alt="" />`)
    return
  }
  if (command === 'link') {
    const href = normalizeLink(safeValue)
    if (!href) return
    const content = selectedHtml || escapeAttribute(href)
    insertHtml(`<a href="${escapeAttribute(href)}" target="_blank" rel="noopener noreferrer">${content}</a>`)
  }
}
