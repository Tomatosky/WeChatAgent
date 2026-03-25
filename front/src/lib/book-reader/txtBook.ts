const SECTION_CHAR_LIMIT = 12000
const HEADING_PATTERN =
  /^(第[〇零一二三四五六七八九十百千万0-9]+[章回节卷篇部].{0,30}|(?:chapter|CHAPTER)\s+\d+.*)$/

interface TxtBookMetadata {
  title: string
  author?: string | null
  language?: string | null
}

interface TxtSectionSource {
  title: string
  content: string
}

interface TxtBookSection {
  id: number
  linear: 'yes'
  size: number
  load: () => string
  unload: () => void
  createDocument: () => Document
}

interface TxtBook {
  sections: TxtBookSection[]
  metadata: {
    title: string
    author?: string | null
    language?: string
  }
  rendition: {
    layout: 'reflowable'
  }
  toc: Array<{
    label: string
    href: string
    subitems: null
  }>
  resolveHref: (href: string) => { index: number }
  isExternal: (href: string) => boolean
  splitTOCHref: (href: string) => [number, null]
  getTOCFragment: (doc: Document) => HTMLElement
  destroy: () => void
}

const escapeHtml = (value: string) =>
  value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')

const normalizeWhitespace = (value: string) =>
  value.replaceAll('\r\n', '\n').replaceAll('\r', '\n').replace(/\u0000/g, '').trim()

const detectBomEncoding = (bytes: Uint8Array): string | null => {
  if (bytes.length >= 3 && bytes[0] === 0xef && bytes[1] === 0xbb && bytes[2] === 0xbf) {
    return 'utf-8'
  }
  if (bytes.length >= 2 && bytes[0] === 0xff && bytes[1] === 0xfe) {
    return 'utf-16le'
  }
  if (bytes.length >= 2 && bytes[0] === 0xfe && bytes[1] === 0xff) {
    return 'utf-16be'
  }
  return null
}

const tryDecode = (buffer: ArrayBuffer, encoding: string): string | null => {
  try {
    return new TextDecoder(encoding, { fatal: true }).decode(buffer)
  } catch {
    return null
  }
}

const scoreDecodedText = (value: string) => {
  const replacementMatches = value.match(/\uFFFD/g) ?? []
  const cjkMatches = value.match(/[\u3400-\u9FFF]/g) ?? []
  const printableMatches = value.match(/[A-Za-z0-9\u3400-\u9FFF，。！？、“”‘’：；（）《》【】,.!?\-_:;"'()\[\]\s]/g) ?? []

  return {
    replacements: replacementMatches.length,
    cjk: cjkMatches.length,
    printable: printableMatches.length,
    length: value.length,
  }
}

const decodeTxtBuffer = (buffer: ArrayBuffer): string => {
  const bytes = new Uint8Array(buffer)
  const bomEncoding = detectBomEncoding(bytes)
  if (bomEncoding) {
    const decoded = tryDecode(buffer, bomEncoding)
    if (decoded) {
      return normalizeWhitespace(decoded.replace(/^\uFEFF/, ''))
    }
  }

  const candidates = ['utf-8', 'gb18030', 'utf-16le', 'utf-16be']
    .map(encoding => ({ encoding, decoded: tryDecode(buffer, encoding) }))
    .filter((item): item is { encoding: string; decoded: string } => Boolean(item.decoded))

  if (!candidates.length) {
    return normalizeWhitespace(new TextDecoder().decode(buffer))
  }

  candidates.sort((left, right) => {
    const a = scoreDecodedText(left.decoded)
    const b = scoreDecodedText(right.decoded)
    if (a.replacements !== b.replacements) return a.replacements - b.replacements
    if (a.cjk !== b.cjk) return b.cjk - a.cjk
    if (a.printable !== b.printable) return b.printable - a.printable
    return b.length - a.length
  })

  return normalizeWhitespace(candidates[0].decoded)
}

const inferLanguage = (text: string, fallback?: string | null) => {
  if (fallback) return fallback
  return /[\u3400-\u9FFF]/.test(text) ? 'zh-CN' : 'en'
}

const splitTxtIntoSections = (text: string): TxtSectionSource[] => {
  if (!text) {
    return [
      {
        title: '正文',
        content: '暂无可显示的正文内容。',
      },
    ]
  }

  const lines = text.split('\n')
  const sections: TxtSectionSource[] = []
  let currentTitle = ''
  let currentLines: string[] = []
  let currentLength = 0

  const flush = () => {
    const content = currentLines.join('\n').trim()
    if (!content && !currentTitle) return
    sections.push({
      title: currentTitle || `第 ${sections.length + 1} 节`,
      content: content || currentTitle,
    })
    currentTitle = ''
    currentLines = []
    currentLength = 0
  }

  for (const rawLine of lines) {
    const line = rawLine.trimEnd()
    const trimmed = line.trim()
    const isHeading = Boolean(trimmed) && trimmed.length <= 40 && HEADING_PATTERN.test(trimmed)

    if (isHeading && (currentLines.length || currentLength > 0)) {
      flush()
    }

    if (isHeading) {
      currentTitle = trimmed
      continue
    }

    currentLines.push(line)
    currentLength += line.length + 1

    if (currentLength >= SECTION_CHAR_LIMIT && !trimmed) {
      flush()
    }
  }

  flush()

  if (!sections.length) {
    return [
      {
        title: '正文',
        content: text,
      },
    ]
  }

  return sections
}

const renderParagraphs = (text: string) => {
  const paragraphs = text
    .split(/\n{2,}/)
    .map(paragraph => paragraph.trim())
    .filter(Boolean)

  if (!paragraphs.length) {
    return '<p>暂无正文内容。</p>'
  }

  return paragraphs
    .map(paragraph => `<p>${escapeHtml(paragraph).replaceAll('\n', '<br>')}</p>`)
    .join('')
}

const renderSectionHtml = (section: TxtSectionSource, metadata: TxtBookMetadata) => {
  const title = escapeHtml(section.title)
  const body = renderParagraphs(section.content)
  const author = metadata.author ? `<p class="reader-author">${escapeHtml(metadata.author)}</p>` : ''
  const language = escapeHtml(metadata.language || 'zh-CN')

  return `<!DOCTYPE html>
<html lang="${language}">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>${title}</title>
    <style>
      html, body {
        margin: 0;
        padding: 0;
        background: #f7f3ea;
        color: #2f2c26;
      }

      body {
        font-family: "Microsoft YaHei", "PingFang SC", "Noto Serif SC", Georgia, serif;
        padding: 2rem 1.5rem 4rem;
        line-height: 1.9;
        word-break: break-word;
      }

      .reader-title {
        margin: 0 0 0.5rem;
        font-size: 1.8rem;
        line-height: 1.3;
        font-weight: 700;
        color: #1f2937;
      }

      .reader-author {
        margin: 0 0 1.5rem;
        font-size: 0.95rem;
        color: #6b7280;
      }

      p {
        margin: 0 0 1rem;
        text-indent: 2em;
      }
    </style>
  </head>
  <body>
    <article>
      <h1 class="reader-title">${title}</h1>
      ${author}
      ${body}
    </article>
  </body>
</html>`
}

export async function makeTxtBook(file: File, metadata: TxtBookMetadata): Promise<TxtBook> {
  const decoded = decodeTxtBuffer(await file.arrayBuffer())
  const language = inferLanguage(decoded, metadata.language)
  const sections = splitTxtIntoSections(decoded)
  const objectUrls = new Set<string>()
  const parser = new DOMParser()

  const txtSections = sections.map<TxtBookSection>((section, index) => {
    const html = renderSectionHtml(section, { ...metadata, language })
    let objectUrl: string | null = null

    return {
      id: index,
      linear: 'yes',
      size: section.content.length,
      load: () => {
        if (!objectUrl) {
          objectUrl = URL.createObjectURL(new Blob([html], { type: 'text/html' }))
          objectUrls.add(objectUrl)
        }
        return objectUrl
      },
      unload: () => {
        if (objectUrl) {
          URL.revokeObjectURL(objectUrl)
          objectUrls.delete(objectUrl)
          objectUrl = null
        }
      },
      createDocument: () => parser.parseFromString(html, 'text/html'),
    }
  })

  const toc = sections.map((section, index) => ({
    label: section.title,
    href: `section:${index}`,
    subitems: null,
  }))

  return {
    sections: txtSections,
    metadata: {
      title: metadata.title,
      author: metadata.author,
      language,
    },
    rendition: {
      layout: 'reflowable',
    },
    toc,
    resolveHref: href => {
      if (href.startsWith('section:')) {
        return { index: Number(href.replace('section:', '')) || 0 }
      }
      return { index: 0 }
    },
    isExternal: href => /^\w+:/i.test(href),
    splitTOCHref: href => [Number(href.replace('section:', '')) || 0, null],
    getTOCFragment: doc => doc.body,
    destroy: () => {
      for (const section of txtSections) {
        section.unload()
      }
      for (const objectUrl of objectUrls) {
        URL.revokeObjectURL(objectUrl)
      }
      objectUrls.clear()
    },
  }
}
