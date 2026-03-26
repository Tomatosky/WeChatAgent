const READER_LOCATION_VERSION = 1
const LOCATION_CACHE_PREFIX = 'weagentchat:book-reading-location:'

interface RawTocItem {
  label?: string | null
  href?: string | null
  subitems?: RawTocItem[] | null
}

interface ReaderProgressDetail {
  fraction?: number
  cfi?: string
  tocItem?: {
    label?: string | null
    href?: string | null
  } | null
  pageItem?: {
    label?: string | null
  } | null
  location?: {
    current?: number | null
  } | null
  section?: {
    current?: number | null
  } | null
  range?: Range | null
}

interface ReaderHistory {
  pushState?: (state: unknown) => void
}

interface ReaderRenderer {
  goTo?: (target: unknown) => Promise<unknown>
  getContents?: () => Array<{
    index?: number | null
    doc?: Document | null
  }>
}

interface ReaderBook {
  toc?: RawTocItem[] | null
  metadata?: {
    title?: string | null
  } | null
}

export interface TocItem {
  label: string
  target: string | null
  children: TocItem[]
  disabled?: boolean
}

export interface StoredReaderLocation {
  v: 1
  f: string
  c?: string
  p?: number
  s?: number
  fr?: number
}

export interface ReaderLocationSnapshot {
  location: StoredReaderLocation | null
  progress: number
  title: string
  detail: string
}

export interface PageContextResult {
  supported: boolean
  reason: string
  text: string
  excerpt: string
  locator: string
  tocPath: string[]
  truncated: boolean
  sourceType: string
}

export interface SelectedQuoteResult {
  text: string
  excerpt: string
  locator: string
  tocPath: string[]
  truncated: boolean
  sourceType: string
}

export interface ReaderViewAdapterTarget {
  book?: ReaderBook | null
  renderer?: ReaderRenderer | null
  lastLocation?: ReaderProgressDetail | null
  history?: ReaderHistory | null
  goTo: (target: unknown) => Promise<unknown>
}

export interface ReaderAdapter {
  getToc: () => TocItem[]
  goToTocItem: (target: TocItem | string) => Promise<void>
  getCurrentLocation: () => ReaderLocationSnapshot | null
  getCurrentContext: () => PageContextResult
  restoreLocation: (location: StoredReaderLocation) => Promise<boolean>
}

const PAGE_CONTEXT_CHAR_LIMIT = 1400
const SELECTED_QUOTE_CHAR_LIMIT = 480

const clampFraction = (value: number | null | undefined) => {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return undefined
  }
  return Math.min(1, Math.max(0, Number(value.toFixed(6))))
}

const toNonNegativeInteger = (value: number | null | undefined) => {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return undefined
  }
  return Math.max(0, Math.floor(value))
}

const trySerializeLocation = (location: StoredReaderLocation) => {
  const serialized = JSON.stringify(location)
  return serialized.length <= 255 ? serialized : null
}

const normalizeTocItems = (items?: RawTocItem[] | null): TocItem[] =>
  (items ?? []).map((item, index) => {
    const children = normalizeTocItems(item.subitems)
    const target = typeof item.href === 'string' && item.href.trim() ? item.href : null

    return {
      label: item.label?.trim() || `未命名章节 ${index + 1}`,
      target,
      children,
      disabled: !target,
    }
  })

const buildLocationDetail = (formatType: string, detail: ReaderProgressDetail, progress: number) => {
  const percentText = `${Math.round(progress * 100)}%`
  const sectionIndex = toNonNegativeInteger(detail.section?.current)

  if (formatType === 'pdf') {
    if (detail.pageItem?.label) {
      return `第 ${detail.pageItem.label} 页`
    }
    if (typeof sectionIndex === 'number') {
      return `第 ${sectionIndex + 1} 页`
    }
    return `阅读进度 ${percentText}`
  }

  if (formatType === 'txt') {
    if (typeof sectionIndex === 'number') {
      return `第 ${sectionIndex + 1} 节 · ${percentText}`
    }
    return `阅读进度 ${percentText}`
  }

  if (detail.pageItem?.label) {
    return `第 ${detail.pageItem.label} 页`
  }
  if (typeof detail.location?.current === 'number') {
    return `位置 ${detail.location.current}`
  }
  return `阅读进度 ${percentText}`
}

const buildStoredLocation = (formatType: string, detail: ReaderProgressDetail): StoredReaderLocation | null => {
  const format = formatType || 'unknown'
  const fraction = clampFraction(detail.fraction)
  const sectionIndex = toNonNegativeInteger(detail.section?.current)

  if (format === 'pdf') {
    if (typeof sectionIndex !== 'number' && typeof fraction !== 'number') {
      return null
    }
    return {
      v: READER_LOCATION_VERSION,
      f: 'pdf',
      p: sectionIndex,
      fr: fraction,
    }
  }

  if (format === 'txt') {
    if (typeof sectionIndex !== 'number' && typeof fraction !== 'number') {
      return null
    }
    return {
      v: READER_LOCATION_VERSION,
      f: 'txt',
      s: sectionIndex,
      fr: fraction,
    }
  }

  const cfi = typeof detail.cfi === 'string' && detail.cfi.trim() ? detail.cfi.trim() : undefined
  if (cfi) {
    const cfiLocation: StoredReaderLocation = {
      v: READER_LOCATION_VERSION,
      f: format,
      c: cfi,
      fr: fraction,
    }
    if (trySerializeLocation(cfiLocation)) {
      return cfiLocation
    }
  }

  if (typeof fraction === 'number') {
    return {
      v: READER_LOCATION_VERSION,
      f: format,
      fr: fraction,
    }
  }

  if (typeof sectionIndex === 'number') {
    return {
      v: READER_LOCATION_VERSION,
      f: format,
      s: sectionIndex,
    }
  }

  return null
}

const normalizeExcerptText = (value: string) =>
  value
    .replace(/\u00A0/g, ' ')
    .replace(/\r\n?/g, '\n')
    .replace(/[ \t]+\n/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .replace(/[ \t]{2,}/g, ' ')
    .trim()

const truncateContextText = (value: string, limit: number) => {
  if (value.length <= limit) {
    return {
      text: value,
      truncated: false,
    }
  }

  return {
    text: `${value.slice(0, Math.max(0, limit - 1)).trimEnd()}…`,
    truncated: true,
  }
}

export const createSelectedQuoteResult = (
  selectedText: string,
  pageContext?: PageContextResult | null,
): SelectedQuoteResult | null => {
  const normalized = normalizeExcerptText(selectedText)
  if (!normalized) {
    return null
  }

  const excerpt = truncateContextText(normalized, SELECTED_QUOTE_CHAR_LIMIT)
  return {
    text: excerpt.text,
    excerpt: excerpt.text,
    locator: pageContext?.locator || '当前位置',
    tocPath: Array.isArray(pageContext?.tocPath) ? pageContext.tocPath : [],
    truncated: excerpt.truncated,
    sourceType: pageContext?.sourceType || 'unknown',
  }
}

const extractTextFromRange = (range?: Range | null) => {
  if (!range) {
    return ''
  }

  try {
    const fragment = range.cloneContents()
    return normalizeExcerptText(fragment.textContent || '')
  } catch {
    return ''
  }
}

const extractTextFromDocument = (doc?: Document | null, selector?: string) => {
  if (!doc) {
    return ''
  }

  const target = selector ? doc.querySelector(selector) : doc.body
  const rawText = target instanceof HTMLElement ? (target.innerText || target.textContent || '') : (target?.textContent || '')
  return normalizeExcerptText(rawText)
}

const getRendererContents = (renderer?: ReaderRenderer | null) => {
  if (!renderer?.getContents) {
    return []
  }

  try {
    const contents = renderer.getContents()
    return Array.isArray(contents) ? contents : []
  } catch {
    return []
  }
}

const getCurrentContentDocument = (
  viewer: ReaderViewAdapterTarget,
  detail: ReaderProgressDetail,
) => {
  const contents = getRendererContents(viewer.renderer)
  const currentSectionIndex = toNonNegativeInteger(detail.section?.current)
  if (typeof currentSectionIndex === 'number') {
    const matched = contents.find(item => toNonNegativeInteger(item.index) === currentSectionIndex)
    if (matched?.doc) {
      return matched.doc
    }
  }
  return contents.find(item => item.doc)?.doc ?? null
}

const findTocPath = (
  items: RawTocItem[] | null | undefined,
  targetLabel?: string | null,
  targetHref?: string | null,
  trail: string[] = [],
): string[] | null => {
  for (const item of items ?? []) {
    const currentLabel = item.label?.trim() || ''
    const nextTrail = currentLabel ? [...trail, currentLabel] : trail
    const sameHref =
      typeof targetHref === 'string' &&
      targetHref.trim() &&
      typeof item.href === 'string' &&
      item.href.trim() === targetHref.trim()
    const sameLabel =
      !targetHref &&
      typeof targetLabel === 'string' &&
      targetLabel.trim() &&
      currentLabel === targetLabel.trim()

    if (sameHref || sameLabel) {
      return nextTrail
    }

    const childMatch = findTocPath(item.subitems, targetLabel, targetHref, nextTrail)
    if (childMatch?.length) {
      return childMatch
    }
  }

  return null
}

const buildPageContext = (
  viewer: ReaderViewAdapterTarget,
  formatType: string,
): PageContextResult => {
  const detail = viewer.lastLocation
  const sourceType =
    formatType === 'pdf'
      ? 'pdf-image-only'
      : formatType === 'txt'
        ? 'txt'
        : formatType || 'unknown'

  if (!detail) {
    return {
      supported: false,
      reason: '阅读器尚未定位到当前页',
      text: '',
      excerpt: '',
      locator: '定位中',
      tocPath: [],
      truncated: false,
      sourceType,
    }
  }

  const progress = clampFraction(detail.fraction) ?? 0
  const locator = buildLocationDetail(formatType, detail, progress)
  const tocPath =
    findTocPath(viewer.book?.toc, detail.tocItem?.label, detail.tocItem?.href) ??
    (detail.tocItem?.label?.trim() ? [detail.tocItem.label.trim()] : [])
  const currentDoc = getCurrentContentDocument(viewer, detail)

  let rawText = ''
  let reason = 'ok'
  let resolvedSourceType = sourceType

  if (formatType === 'pdf') {
    rawText =
      extractTextFromRange(detail.range) ||
      extractTextFromDocument(currentDoc, '.textLayer') ||
      extractTextFromDocument(currentDoc)
    resolvedSourceType = rawText ? 'pdf-text-layer' : 'pdf-image-only'
    if (!rawText) {
      reason = '当前 PDF 页面没有可提取文本层'
    }
  } else {
    rawText = extractTextFromRange(detail.range) || extractTextFromDocument(currentDoc)
    if (!rawText) {
      reason = '当前页正文为空或暂不可提取'
    }
  }

  if (!rawText) {
    return {
      supported: false,
      reason,
      text: '',
      excerpt: '',
      locator,
      tocPath,
      truncated: false,
      sourceType: resolvedSourceType,
    }
  }

  const excerpt = truncateContextText(rawText, PAGE_CONTEXT_CHAR_LIMIT)

  return {
    supported: true,
    reason: excerpt.truncated ? '当前页正文过长，已按上限截断' : 'ok',
    text: excerpt.text,
    excerpt: excerpt.text,
    locator,
    tocPath,
    truncated: excerpt.truncated,
    sourceType: resolvedSourceType,
  }
}

const coerceLocationObject = (value: unknown, formatHint?: string): StoredReaderLocation | null => {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return null
  }

  const candidate = value as Record<string, unknown>
  const format = typeof candidate.f === 'string' && candidate.f.trim() ? candidate.f.trim() : (formatHint || 'unknown')

  if (candidate.v === READER_LOCATION_VERSION) {
    return {
      v: READER_LOCATION_VERSION,
      f: format,
      c: typeof candidate.c === 'string' && candidate.c.trim() ? candidate.c.trim() : undefined,
      p: toNonNegativeInteger(candidate.p as number | undefined),
      s: toNonNegativeInteger(candidate.s as number | undefined),
      fr: clampFraction(candidate.fr as number | undefined),
    }
  }

  if (typeof candidate.cfi === 'string' && candidate.cfi.trim()) {
    return {
      v: READER_LOCATION_VERSION,
      f: format,
      c: candidate.cfi.trim(),
      fr: clampFraction(candidate.fraction as number | undefined),
    }
  }

  if (typeof candidate.pageIndex === 'number') {
    return {
      v: READER_LOCATION_VERSION,
      f: formatHint || 'pdf',
      p: toNonNegativeInteger(candidate.pageIndex),
      fr: clampFraction(candidate.fraction as number | undefined),
    }
  }

  if (typeof candidate.sectionIndex === 'number') {
    return {
      v: READER_LOCATION_VERSION,
      f: formatHint || 'txt',
      s: toNonNegativeInteger(candidate.sectionIndex),
      fr: clampFraction(candidate.fraction as number | undefined),
    }
  }

  if (typeof candidate.fraction === 'number') {
    return {
      v: READER_LOCATION_VERSION,
      f: format,
      fr: clampFraction(candidate.fraction),
    }
  }

  return null
}

export const parseStoredReaderLocation = (
  rawValue?: string | null,
  formatHint?: string,
): StoredReaderLocation | null => {
  if (!rawValue) {
    return null
  }

  const trimmed = rawValue.trim()
  if (!trimmed) {
    return null
  }

  if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
    try {
      return coerceLocationObject(JSON.parse(trimmed), formatHint)
    } catch {
      return null
    }
  }

  if (trimmed.startsWith('epubcfi(')) {
    return {
      v: READER_LOCATION_VERSION,
      f: formatHint || 'epub',
      c: trimmed,
    }
  }

  if (trimmed.startsWith('fraction:')) {
    const fraction = clampFraction(Number(trimmed.replace('fraction:', '')))
    if (typeof fraction === 'number') {
      return {
        v: READER_LOCATION_VERSION,
        f: formatHint || 'unknown',
        fr: fraction,
      }
    }
    return null
  }

  if (/^-?\d+(\.\d+)?$/.test(trimmed)) {
    const numeric = Number(trimmed)
    if (!Number.isFinite(numeric)) {
      return null
    }

    if (formatHint === 'pdf' && Number.isInteger(numeric)) {
      return {
        v: READER_LOCATION_VERSION,
        f: 'pdf',
        p: Math.max(0, numeric),
      }
    }

    return {
      v: READER_LOCATION_VERSION,
      f: formatHint || 'unknown',
      fr: clampFraction(numeric),
    }
  }

  return null
}

export const serializeStoredReaderLocation = (location: StoredReaderLocation | null) => {
  if (!location) {
    return null
  }
  return trySerializeLocation(location)
}

export const loadCachedReadingLocation = (bookId: number, formatHint?: string) => {
  try {
    const cached = window.localStorage.getItem(`${LOCATION_CACHE_PREFIX}${bookId}`)
    return parseStoredReaderLocation(cached, formatHint)
  } catch {
    return null
  }
}

export const cacheReadingLocation = (bookId: number, serializedLocation: string | null) => {
  try {
    const storageKey = `${LOCATION_CACHE_PREFIX}${bookId}`
    if (serializedLocation) {
      window.localStorage.setItem(storageKey, serializedLocation)
    } else {
      window.localStorage.removeItem(storageKey)
    }
  } catch {
    // ignore storage failures
  }
}

export const createReaderAdapter = (
  viewer: ReaderViewAdapterTarget,
  formatType: string,
  fallbackTitle: string,
): ReaderAdapter => ({
  getToc: () => normalizeTocItems(viewer.book?.toc),
  goToTocItem: async target => {
    const resolvedTarget = typeof target === 'string' ? target : target.target
    if (!resolvedTarget) {
      return
    }
    await viewer.goTo(resolvedTarget)
  },
  getCurrentLocation: () => {
    const detail = viewer.lastLocation
    if (!detail) {
      return null
    }

    const progress = clampFraction(detail.fraction) ?? 0
    const title =
      detail.tocItem?.label?.trim() ||
      viewer.book?.metadata?.title?.trim() ||
      fallbackTitle ||
      '当前位置'

    return {
      location: buildStoredLocation(formatType, detail),
      progress,
      title,
      detail: buildLocationDetail(formatType, detail, progress),
    }
  },
  getCurrentContext: () => buildPageContext(viewer, formatType),
  restoreLocation: async location => {
    try {
      if (formatType === 'pdf' && typeof location.p === 'number') {
        await viewer.goTo(location.p)
        return true
      }

      if (typeof location.c === 'string' && location.c) {
        await viewer.goTo(location.c)
        return true
      }

      if (typeof location.fr === 'number') {
        await viewer.goTo({ fraction: location.fr })
        return true
      }

      if (typeof location.s === 'number') {
        if (viewer.renderer?.goTo) {
          await viewer.renderer.goTo({ index: location.s, anchor: 0 })
          viewer.history?.pushState?.(location.s)
          return true
        }
        await viewer.goTo(location.s)
        return true
      }

      if (typeof location.p === 'number') {
        await viewer.goTo(location.p)
        return true
      }
    } catch (error) {
      console.warn('restore reading location failed', error)
    }

    return false
  },
})
