<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import {
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  Columns2,
  ListTree,
  LoaderCircle,
  MoreHorizontal,
  ScrollText,
  Check,
} from 'lucide-vue-next'

import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu'

import type { SelectedQuotePayload } from '@/api/chat'
import { updateBookReadingLocation, type Book } from '@/api/book'
import { getStaticUrl } from '@/api/base'
import BookReadingChatPanel from '@/components/book-reader/BookReadingChatPanel.vue'
import ReaderTocPanel from '@/components/book-reader/ReaderTocPanel.vue'
import { useToast } from '@/composables/useToast'
import { loadFoliateViewModule, type FoliateViewRuntimeModule } from '@/lib/book-reader/foliate'
import {
  cacheReadingLocation,
  createSelectedQuoteResult,
  createReaderAdapter,
  loadCachedReadingLocation,
  parseStoredReaderLocation,
  serializeStoredReaderLocation,
  type ReaderAdapter,
  type PageContextResult,
  type TocItem,
} from '@/lib/book-reader/readerAdapter'
import { makeTxtBook } from '@/lib/book-reader/txtBook'

const props = defineProps<{
  book: Book
}>()

const emit = defineEmits<{
  (e: 'back'): void
}>()

interface FoliateRendererElement extends HTMLElement {
  setStyles?: (styles: string) => void
  goTo?: (target: unknown) => Promise<void>
}

interface FoliateTocItem {
  label?: string | null
  href?: string | null
  subitems?: FoliateTocItem[] | null
}

interface FoliateViewElement extends HTMLElement {
  book?: {
    toc?: FoliateTocItem[]
    metadata?: {
      title?: string | null
    } | null
  } | null
  renderer?: FoliateRendererElement
  isFixedLayout?: boolean
  history?: {
    pushState?: (state: unknown) => void
  }
  open: (book: unknown) => Promise<void>
  init: (options: { lastLocation?: unknown; showTextStart?: boolean }) => Promise<void>
  goTo: (target: unknown) => Promise<void>
  close: () => void
  prev: (distance?: number) => Promise<void>
  next: (distance?: number) => Promise<void>
  goLeft: () => Promise<void>
  goRight: () => Promise<void>
  deselect?: () => void
}

interface FoliateLoadEventDetail {
  doc?: Document | null
  index?: number | null
}

interface DocumentSelectionHandlers {
  selectionchange: () => void
  mouseup: () => void
  keyup: () => void
}

interface ReaderBookSource {
  destroy?: () => void
}

interface ReaderBanner {
  tone: 'warn'
  title: string
  detail: string
}

const LOCATION_PERSIST_DEBOUNCE_MS = 1200

const toast = useToast()
const viewerHost = ref<HTMLElement | null>(null)
const viewer = shallowRef<FoliateViewElement | null>(null)
const openedBookSource = shallowRef<ReaderBookSource | null>(null)
const readerAdapter = shallowRef<ReaderAdapter | null>(null)
const isLoading = ref(false)
const loadError = ref<string | null>(null)
const flowMode = ref<'paginated' | 'scrolled'>('paginated')
const currentProgress = ref(0)
const currentLabel = ref('等待打开')
const currentDetail = ref('进入阅读器后可使用上一页 / 下一页浏览')
const currentPageContext = ref<PageContextResult | null>(null)
const selectedQuote = ref<SelectedQuotePayload | null>(null)
const tocItems = ref<TocItem[]>([])
const isTocOpen = ref(false)
const isChatCollapsed = ref(false)
const isLeaving = ref(false)
const lastPersistedLocation = ref<string | null>(null)
const selectionBindings = new Map<Document, DocumentSelectionHandlers>()
let openVersion = 0
let persistTimer: number | null = null

const bookFileUrl = computed(() => getStaticUrl(props.book.file_path) ?? '')
const isBlockedByStatus = computed(() => ['processing', 'failed'].includes(props.book.status))
const showModeToggle = computed(() => Boolean(viewer.value) && !viewer.value?.isFixedLayout)
const showReaderChrome = computed(() => !isBlockedByStatus.value && !loadError.value)

const readerState = computed(() => {
  if (props.book.status === 'processing') {
    return {
      title: '图书还在处理中',
      detail: props.book.status_detail || '正文、目录和结构信息正在准备中，稍后再回来阅读。',
      tone: 'warn' as const,
    }
  }

  if (props.book.status === 'failed') {
    return {
      title: '这本书暂时无法打开',
      detail: props.book.status_detail || '图书解析失败或当前设备暂不支持渲染。',
      tone: 'warn' as const,
    }
  }

  return null
})

const banners = computed<ReaderBanner[]>(() => {
  if (readerState.value) {
    return []
  }

  const items: ReaderBanner[] = []

  if (props.book.status === 'limited') {
    items.push({
      tone: 'warn',
      title: '能力受限',
      detail: props.book.status_detail || '这本书当前只能使用部分阅读能力，请以页面提示为准。',
    })
  }

  return items
})

const headerSubtitle = computed(() => {
  return props.book.author?.trim() || '原作者待补充'
})



const getReaderContentStyles = () => `
  @namespace epub "http://www.idpf.org/2007/ops";
  html {
    color-scheme: light;
  }

  body {
    color: #2f2c26;
    background: #f7f3ea;
  }

  p, li, blockquote, dd {
    line-height: 1.92;
    text-align: justify;
    -webkit-hyphens: auto;
    hyphens: auto;
    hanging-punctuation: allow-end last;
    widows: 2;
  }

  img, svg, video, canvas {
    max-width: 100%;
    height: auto;
  }

  pre {
    white-space: pre-wrap !important;
  }
`

const clearPersistTimer = () => {
  if (persistTimer !== null) {
    window.clearTimeout(persistTimer)
    persistTimer = null
  }
}

const resetReaderState = () => {
  currentProgress.value = 0
  currentLabel.value = '正在准备正文...'
  currentDetail.value = '阅读器'
  currentPageContext.value = null
  selectedQuote.value = null
  tocItems.value = []
  isTocOpen.value = false
}

const clearSelectedQuote = (options: { clearViewerSelection?: boolean } = {}) => {
  selectedQuote.value = null
  if (options.clearViewerSelection) {
    try {
      viewer.value?.deselect?.()
    } catch {
      // ignore selection clear failures
    }
  }
}

const removeDocumentSelectionListeners = () => {
  for (const [doc, handlers] of selectionBindings.entries()) {
    doc.removeEventListener('selectionchange', handlers.selectionchange)
    doc.removeEventListener('mouseup', handlers.mouseup)
    doc.removeEventListener('keyup', handlers.keyup)
  }
  selectionBindings.clear()
}

const syncSelectedQuoteFromDocument = (doc?: Document | null) => {
  if (!doc) {
    return
  }

  const selection = doc.defaultView?.getSelection()
  const rawText = selection?.toString() || ''
  if (!rawText.trim()) {
    return
  }

  const quote = createSelectedQuoteResult(
    rawText,
    readerAdapter.value?.getCurrentContext() ?? currentPageContext.value,
  )
  if (!quote) {
    return
  }

  selectedQuote.value = {
    text: quote.text,
    excerpt: quote.excerpt,
    locator: quote.locator,
    tocPath: quote.tocPath,
    truncated: quote.truncated,
    sourceType: quote.sourceType,
  }
}

const bindDocumentSelectionListeners = (doc?: Document | null) => {
  if (!doc || selectionBindings.has(doc)) {
    return
  }

  const sync = () => {
    syncSelectedQuoteFromDocument(doc)
  }
  const handlers: DocumentSelectionHandlers = {
    selectionchange: sync,
    mouseup: sync,
    keyup: sync,
  }

  doc.addEventListener('selectionchange', handlers.selectionchange)
  doc.addEventListener('mouseup', handlers.mouseup)
  doc.addEventListener('keyup', handlers.keyup)
  selectionBindings.set(doc, handlers)
}

const cleanupReader = () => {
  clearPersistTimer()
  removeDocumentSelectionListeners()
  clearSelectedQuote()

  if (viewer.value) {
    viewer.value.removeEventListener('load', handleFoliateLoad as EventListener)
    viewer.value.removeEventListener('relocate', handleRelocate)

    try {
      viewer.value.close()
    } catch {
      // ignore close failures
    }

    viewer.value.remove()
    viewer.value = null
  }

  try {
    openedBookSource.value?.destroy?.()
  } catch {
    // ignore source cleanup failures
  }

  openedBookSource.value = null
  readerAdapter.value = null
  tocItems.value = []

  if (viewerHost.value) {
    viewerHost.value.replaceChildren()
  }
}

const applyRendererPreferences = () => {
  const currentViewer = viewer.value
  const renderer = currentViewer?.renderer
  if (!currentViewer || !renderer) return

  renderer.setStyles?.(getReaderContentStyles())

  if (currentViewer.isFixedLayout) return

  renderer.setAttribute('flow', flowMode.value)
  renderer.setAttribute('gap', '7%')
  renderer.setAttribute('margin', '56px')
  renderer.setAttribute('max-inline-size', '760px')
  renderer.setAttribute('max-block-size', '980px')
  renderer.setAttribute('animated', '')
}

const handleFoliateLoad = (event: Event) => {
  applyRendererPreferences()
  bindDocumentSelectionListeners((event as CustomEvent<FoliateLoadEventDetail>).detail?.doc)
}

const getInitialStoredLocation = () =>
  loadCachedReadingLocation(props.book.id, props.book.format_type) ??
  parseStoredReaderLocation(props.book.reading_location, props.book.format_type)

const getCurrentPersistPayload = () => {
  const snapshot = readerAdapter.value?.getCurrentLocation()
  if (!snapshot?.location) {
    return null
  }

  const readingLocation = serializeStoredReaderLocation(snapshot.location)
  if (!readingLocation) {
    return null
  }

  return {
    reading_location: readingLocation,
    progress: Number(snapshot.progress.toFixed(6)),
    display_label: snapshot.detail,
  }
}

const persistReadingLocation = async (options: { keepalive?: boolean } = {}) => {
  const payload = getCurrentPersistPayload()
  if (!payload) {
    return
  }

  cacheReadingLocation(props.book.id, payload.reading_location)
  if (payload.reading_location === lastPersistedLocation.value) {
    return
  }

  try {
    await updateBookReadingLocation(props.book.id, payload, {
      keepalive: options.keepalive,
    })
    lastPersistedLocation.value = payload.reading_location
  } catch (error) {
    console.warn('保存阅读进度失败', error)
  }
}

const scheduleReadingLocationPersist = () => {
  clearPersistTimer()
  persistTimer = window.setTimeout(() => {
    persistTimer = null
    void persistReadingLocation()
  }, LOCATION_PERSIST_DEBOUNCE_MS)
}

const flushReadingLocationPersist = async (options: { keepalive?: boolean } = {}) => {
  clearPersistTimer()
  await persistReadingLocation(options)
}

const triggerExitPersistence = () => {
  clearPersistTimer()
  void persistReadingLocation({ keepalive: true })
}

const syncReaderRuntimeState = () => {
  const snapshot = readerAdapter.value?.getCurrentLocation()
  if (snapshot) {
    currentProgress.value = snapshot.progress
    currentLabel.value = snapshot.title
    currentDetail.value = snapshot.detail
  }
  currentPageContext.value = readerAdapter.value?.getCurrentContext() ?? null
}

const handleRelocate = (_event: Event) => {
  clearSelectedQuote({ clearViewerSelection: true })
  syncReaderRuntimeState()
  scheduleReadingLocationPersist()
}

const createReaderSource = async (): Promise<unknown> => {
  if (!bookFileUrl.value) {
    throw new Error('图书文件地址无效，无法打开。')
  }

  if (props.book.format_type === 'txt') {
    const response = await fetch(bookFileUrl.value)
    if (!response.ok) {
      throw new Error(`读取 TXT 文件失败（${response.status} ${response.statusText}）`)
    }

    const blob = await response.blob()
    const file = new File([blob], props.book.file_name, {
      type: blob.type || 'text/plain',
    })
    const txtBook = await makeTxtBook(file, {
      title: props.book.title,
      author: props.book.author,
    })
    return txtBook
  }

  return bookFileUrl.value
}

const openReader = async () => {
  const currentOpenVersion = ++openVersion
  cleanupReader()
  resetReaderState()
  loadError.value = null
  lastPersistedLocation.value = null

  if (!viewerHost.value || isBlockedByStatus.value) {
    return
  }

  isLoading.value = true
  let foliateModule: FoliateViewRuntimeModule | null = null

  try {
    foliateModule = await loadFoliateViewModule()
    if (currentOpenVersion !== openVersion || !viewerHost.value) return

    const element = document.createElement('foliate-view') as FoliateViewElement
    element.className = 'reader-element'
    element.style.display = 'block'
    element.style.width = '100%'
    element.style.height = '100%'
    element.addEventListener('load', handleFoliateLoad as EventListener)
    element.addEventListener('relocate', handleRelocate)

    viewerHost.value.replaceChildren(element)
    viewer.value = element

    const source = await createReaderSource()
    if (currentOpenVersion !== openVersion) {
      if (typeof source !== 'string') {
        ;(source as ReaderBookSource).destroy?.()
      }
      return
    }
    openedBookSource.value = typeof source === 'string' ? null : (source as ReaderBookSource)

    await element.open(source)
    applyRendererPreferences()

    readerAdapter.value = createReaderAdapter(element, props.book.format_type, props.book.title)
    tocItems.value = readerAdapter.value.getToc()

    if (element.isFixedLayout) {
      flowMode.value = 'paginated'
    }

    const initialLocation = getInitialStoredLocation()
    lastPersistedLocation.value = serializeStoredReaderLocation(initialLocation)

    const restored = initialLocation ? await readerAdapter.value.restoreLocation(initialLocation) : false
    if (!restored) {
      await element.init({
        showTextStart: true,
      })
    }
    syncReaderRuntimeState()
  } catch (error) {
    cleanupReader()

    if (foliateModule && error instanceof foliateModule.UnsupportedTypeError) {
      loadError.value = '当前格式还没有可用的阅读适配器。'
    } else if (foliateModule && error instanceof foliateModule.NotFoundError) {
      loadError.value = '找不到这本书对应的文件，请返回图书馆后重新导入。'
    } else if (foliateModule && error instanceof foliateModule.ResponseError) {
      loadError.value = '图书文件读取失败，请稍后重试。'
    } else {
      loadError.value = error instanceof Error ? error.message : '阅读器打开失败。'
    }

    toast.error(loadError.value)
  } finally {
    if (currentOpenVersion === openVersion) {
      isLoading.value = false
    }
  }
}

const goPrev = async () => {
  if (!viewer.value || isLoading.value) return
  await viewer.value.goLeft()
}

const goNext = async () => {
  if (!viewer.value || isLoading.value) return
  await viewer.value.goRight()
}

const handleTocSelect = async (item: TocItem) => {
  if (!readerAdapter.value || item.disabled) {
    return
  }

  try {
    await readerAdapter.value.goToTocItem(item)
    isTocOpen.value = false
  } catch (error) {
    const message = error instanceof Error ? error.message : '目录跳转失败'
    toast.error(message)
  }
}

const handleBack = async () => {
  if (isLeaving.value) {
    return
  }

  isLeaving.value = true
  try {
    await flushReadingLocationPersist()
  } finally {
    isLeaving.value = false
    emit('back')
  }
}

const handleRetry = () => {
  void openReader()
}

const handleKeydown = (event: KeyboardEvent) => {
  if (!viewer.value || isLoading.value) return
  if (event.defaultPrevented || event.metaKey || event.ctrlKey || event.altKey) return

  const target = event.target as HTMLElement | null
  if (target?.closest('[data-reader-chat-panel]')) return
  if (target && ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName)) return

  if (event.key === 'ArrowLeft' || event.key === 'PageUp') {
    event.preventDefault()
    void goPrev()
  }

  if (event.key === 'ArrowRight' || event.key === 'PageDown' || event.key === ' ') {
    event.preventDefault()
    void goNext()
  }

  if (event.key.toLowerCase() === 'escape') {
    event.preventDefault()
    void handleBack()
  }
}

const handleVisibilityChange = () => {
  if (document.visibilityState === 'hidden') {
    triggerExitPersistence()
  }
}

const handleWindowBlur = () => {
  triggerExitPersistence()
}

const handlePageHide = () => {
  triggerExitPersistence()
}

const handleBeforeUnload = () => {
  triggerExitPersistence()
}

watch(flowMode, value => {
  if (!viewer.value?.renderer || viewer.value.isFixedLayout) return
  viewer.value.renderer.setAttribute('flow', value)
})

watch(
  () => `${props.book.id}:${props.book.status}:${props.book.file_path}`,
  () => {
    flowMode.value = 'paginated'
    void openReader()
  },
)

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
  window.addEventListener('blur', handleWindowBlur)
  window.addEventListener('pagehide', handlePageHide)
  window.addEventListener('beforeunload', handleBeforeUnload)
  document.addEventListener('visibilitychange', handleVisibilityChange)
  void openReader()
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeydown)
  window.removeEventListener('blur', handleWindowBlur)
  window.removeEventListener('pagehide', handlePageHide)
  window.removeEventListener('beforeunload', handleBeforeUnload)
  document.removeEventListener('visibilitychange', handleVisibilityChange)
  triggerExitPersistence()
  openVersion += 1
  cleanupReader()
})
</script>

<template>
  <div class="book-reader-page">
    <header class="reader-header">
      <div class="reader-header-main">
        <div class="reader-title-wrap">
          <h1 class="reader-title">{{ book.title }}</h1>
          <p class="reader-subtitle">{{ headerSubtitle }}</p>
        </div>
      </div>

      <div class="reader-header-actions">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button class="header-btn secondary" type="button" :disabled="isLoading || !showReaderChrome || isLeaving">
              <MoreHorizontal :size="16" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" class="w-40">
            <DropdownMenuItem @click="isTocOpen = true">
              <ListTree :size="14" class="mr-2" />
              <span>目录</span>
            </DropdownMenuItem>

            <template v-if="showModeToggle">
              <DropdownMenuSeparator />
              <DropdownMenuItem @click="flowMode = 'paginated'" :class="{ 'bg-muted': flowMode === 'paginated' }">
                <Columns2 :size="14" class="mr-2" />
                <span>分页阅读</span>
                <Check v-if="flowMode === 'paginated'" :size="14" class="ml-auto" />
              </DropdownMenuItem>
              <DropdownMenuItem @click="flowMode = 'scrolled'" :class="{ 'bg-muted': flowMode === 'scrolled' }">
                <ScrollText :size="14" class="mr-2" />
                <span>滚动阅读</span>
                <Check v-if="flowMode === 'scrolled'" :size="14" class="ml-auto" />
              </DropdownMenuItem>
            </template>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>

    <div v-if="banners.length" class="reader-banners">
      <article
        v-for="banner in banners"
        :key="`${banner.title}-${banner.detail}`"
        class="banner-card"
        :class="banner.tone"
      >
        <AlertTriangle :size="16" />
        <div>
          <p class="banner-title">{{ banner.title }}</p>
          <p class="banner-detail">{{ banner.detail }}</p>
        </div>
      </article>
    </div>

    <main class="reader-stage">
      <div class="reader-stage-layout" :class="{ 'chat-collapsed': isChatCollapsed }">
        <section class="reader-paper">
          <div
            ref="viewerHost"
            class="viewer-host"
            :class="{ muted: isLoading || Boolean(readerState) || Boolean(loadError) }"
          />

          <button
            v-if="showReaderChrome"
            type="button"
            class="nav-hotspot nav-prev"
            :disabled="isLoading || isLeaving"
            aria-label="上一页"
            @click="goPrev"
          >
            <ChevronLeft :size="18" />
          </button>

          <button
            v-if="showReaderChrome"
            type="button"
            class="nav-hotspot nav-next"
            :disabled="isLoading || isLeaving"
            aria-label="下一页"
            @click="goNext"
          >
            <ChevronRight :size="18" />
          </button>

          <div v-if="isLoading" class="reader-overlay">
            <LoaderCircle :size="28" class="spinning text-green" />
            <h2>正在排版正文</h2>
            <p>阅读器正在加载《{{ book.title }}》，稍等片刻即可开始阅读。</p>
          </div>

          <div v-else-if="readerState" class="reader-overlay">
            <AlertTriangle :size="28" class="text-amber" />
            <h2>{{ readerState.title }}</h2>
            <p>{{ readerState.detail }}</p>
            <div class="overlay-actions">
              <button class="overlay-btn secondary" type="button" @click="handleBack">返回图书馆</button>
            </div>
          </div>

          <div v-else-if="loadError" class="reader-overlay">
            <AlertTriangle :size="28" class="text-amber" />
            <h2>阅读器打开失败</h2>
            <p>{{ loadError }}</p>
            <div class="overlay-actions">
              <button class="overlay-btn secondary" type="button" @click="handleBack">返回图书馆</button>
              <button class="overlay-btn primary" type="button" @click="handleRetry">重试打开</button>
            </div>
          </div>
        </section>

        <BookReadingChatPanel
          class="reader-chat-aside"
          :book="book"
          :collapsed="isChatCollapsed"
          :page-context="currentPageContext"
          :selected-quote="selectedQuote"
          @toggle-collapse="isChatCollapsed = !isChatCollapsed"
          @clear-selected-quote="clearSelectedQuote({ clearViewerSelection: true })"
        />
      </div>
    </main>



    <ReaderTocPanel
      :open="isTocOpen"
      :items="tocItems"
      :active-label="currentLabel"
      @update:open="isTocOpen = $event"
      @select="handleTocSelect"
    />
  </div>
</template>

<style scoped>
.book-reader-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  background:
    radial-gradient(circle at top left, rgba(7, 193, 96, 0.12), transparent 22%),
    radial-gradient(circle at top right, rgba(15, 23, 42, 0.05), transparent 20%),
    linear-gradient(180deg, #f6f8f6 0%, #eef2ef 100%);
}

.reader-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px 20px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(18px);
}

.reader-header-main {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
}

.reader-title-wrap {
  display: flex;
  align-items: baseline;
  gap: 10px;
  min-width: 0;
}

.reader-title {
  margin: 0;
  font-size: 16px;
  line-height: 1.25;
  font-weight: 600;
  color: #0f172a;
}

.reader-subtitle {
  margin: 0;
  font-size: 13px;
  color: #64748b;
}

.reader-header-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
}

.header-btn,
.mode-btn,
.overlay-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.header-btn {
  height: 32px;
  padding: 0 12px;
  background: #07c160;
  color: #fff;
  font-size: 13px;
  box-shadow: 0 4px 12px rgba(7, 193, 96, 0.18);
}

.header-btn:hover:not(:disabled) {
  background: #06ad56;
}

.header-btn.secondary {
  background: rgba(255, 255, 255, 0.88);
  color: #475569;
  border: 1px solid rgba(148, 163, 184, 0.2);
  box-shadow: none;
}

.header-btn.secondary:hover:not(:disabled) {
  border-color: rgba(100, 116, 139, 0.28);
  color: #1f2937;
  background: #f8fafc;
}

.header-btn:disabled,
.mode-btn:disabled,
.overlay-btn:disabled,
.footer-btn:disabled,
.nav-hotspot:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.mode-switch {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid rgba(148, 163, 184, 0.18);
}

.mode-btn {
  height: 32px;
  padding: 0 12px;
  background: transparent;
  color: #64748b;
  font-size: 13px;
  font-weight: 600;
}

.mode-btn.active {
  background: rgba(7, 193, 96, 0.12);
  color: #087443;
}

.reader-banners {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 10px;
  padding: 12px 24px 0;
}

.banner-card {
  display: flex;
  gap: 10px;
  padding: 12px 14px;
  border-radius: 16px;
  border: 1px solid transparent;
}

.banner-card.neutral {
  background: rgba(255, 255, 255, 0.78);
  border-color: rgba(148, 163, 184, 0.14);
  color: #334155;
}

.banner-card.warn {
  background: rgba(255, 247, 237, 0.92);
  border-color: rgba(251, 191, 36, 0.24);
  color: #92400e;
}

.banner-title {
  margin: 0;
  font-size: 13px;
  font-weight: 700;
}

.banner-detail {
  margin: 3px 0 0;
  font-size: 12px;
  line-height: 1.6;
}

.reader-stage {
  flex: 1;
  min-height: 0;
  padding: 16px 24px;
}

.reader-stage-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(320px, 30%);
  gap: 16px;
  height: 100%;
  min-height: 0;
}

.reader-stage-layout.chat-collapsed {
  grid-template-columns: minmax(0, 1fr) 68px;
}

.reader-paper {
  position: relative;
  height: 100%;
  min-height: 0;
  border-radius: 28px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.92);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.88) 0%, rgba(247, 243, 234, 0.92) 100%);
  box-shadow:
    0 24px 60px rgba(15, 23, 42, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.72);
}

.reader-chat-aside {
  min-height: 0;
}

.viewer-host {
  height: 100%;
  min-height: 0;
  transition: opacity 0.2s ease;
}

.viewer-host.muted {
  opacity: 0.15;
  pointer-events: none;
}

:deep(.reader-element) {
  display: block;
  width: 100%;
  height: 100%;
}

:deep(.reader-element::part(filter)) {
  background:
    radial-gradient(circle at top, rgba(255, 255, 255, 0.72), transparent 28%),
    #f7f3ea;
}

.nav-hotspot {
  position: absolute;
  top: 50%;
  z-index: 3;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 84px;
  border: none;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.82);
  color: #334155;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
  transform: translateY(-50%);
  cursor: pointer;
  transition: all 0.2s ease;
}

.nav-hotspot:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.96);
  color: #07c160;
}

.nav-prev {
  left: 18px;
}

.nav-next {
  right: 18px;
}

.reader-overlay {
  position: absolute;
  inset: 0;
  z-index: 2;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 28px;
  text-align: center;
  background: rgba(247, 243, 234, 0.9);
  backdrop-filter: blur(8px);
}

.reader-overlay h2 {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  color: #0f172a;
}

.reader-overlay p {
  max-width: 420px;
  margin: 0;
  font-size: 14px;
  line-height: 1.7;
  color: #64748b;
}

.overlay-actions {
  display: flex;
  gap: 10px;
  margin-top: 10px;
}

.overlay-btn {
  height: 38px;
  padding: 0 16px;
  font-size: 13px;
  font-weight: 600;
}

.overlay-btn.primary {
  background: #07c160;
  color: #fff;
}

.overlay-btn.secondary {
  background: rgba(255, 255, 255, 0.86);
  color: #334155;
  border: 1px solid rgba(148, 163, 184, 0.24);
}



.text-green {
  color: #07c160;
}

.text-amber {
  color: #d97706;
}

.spinning {
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 900px) {
  .reader-header,
  .reader-stage,
  .reader-banners {
    padding-left: 16px;
    padding-right: 16px;
  }

  .reader-header {
    flex-direction: column;
    align-items: stretch;
  }

  .reader-header-actions {
    width: 100%;
    justify-content: space-between;
  }

  .mode-switch {
    flex: 1;
  }

  .mode-btn {
    flex: 1;
  }

  .reader-title {
    font-size: 20px;
  }

  .nav-hotspot {
    width: 40px;
    height: 72px;
  }

  .reader-stage-layout,
  .reader-stage-layout.chat-collapsed {
    grid-template-columns: minmax(0, 1fr);
    grid-template-rows: minmax(0, 1fr) auto;
  }
}

@media (max-width: 640px) {
  .reader-header-main {
    align-items: flex-start;
  }

  .header-btn,
  .overlay-btn {
    flex: 1;
  }

  .reader-stage {
    padding-top: 12px;
    padding-bottom: 12px;
  }

  .reader-paper {
    border-radius: 20px;
  }

  .nav-hotspot {
    top: auto;
    bottom: 18px;
    transform: none;
    height: 42px;
    width: 42px;
    border-radius: 999px;
  }

  .nav-prev {
    left: 16px;
  }

  .nav-next {
    right: 16px;
  }

  .overlay-actions {
    width: 100%;
    flex-direction: column;
  }
}
</style>
