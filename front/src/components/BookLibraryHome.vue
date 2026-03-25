<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  BookOpen,
  FilePlus2,
  LoaderCircle,
  RefreshCw,
} from 'lucide-vue-next'

import { getStaticUrl } from '@/api/base'
import { getBooks, importBook, type Book } from '@/api/book'
import { useToast } from '@/composables/useToast'

const emit = defineEmits<{
  (e: 'back-chat'): void
}>()

const toast = useToast()
const isElectron = Boolean(window.WeAgentChat?.windowControls)
const fileInput = ref<HTMLInputElement | null>(null)
const books = ref<Book[]>([])
const isLoading = ref(false)
const isImporting = ref(false)

const MAX_BOOK_FILE_SIZE = 200 * 1024 * 1024
const accept = '.epub,.pdf,.mobi,.azw,.azw3,.txt'
const allowedExtensions = new Set(['.epub', '.pdf', '.mobi', '.azw', '.azw3', '.txt'])

const totalBooks = computed(() => books.value.length)

const handleToggleMaximize = () => {
  if (!isElectron) return
  window.WeAgentChat?.windowControls?.toggleMaximize()
}

const handleHeaderContextMenu = (event: MouseEvent) => {
  if (!isElectron) return
  event.preventDefault()
  window.WeAgentChat?.windowControls?.showSystemMenu({
    x: event.screenX,
    y: event.screenY,
  })
}

const getStatusLabel = (status: string) => {
  switch (status) {
    case 'imported':
      return '已导入'
    case 'processing':
      return '处理中'
    case 'ready':
      return '可阅读'
    case 'limited':
      return '受限可用'
    case 'failed':
      return '导入失败'
    default:
      return status
  }
}

const getFormatLabel = (formatType: string) => formatType.toUpperCase()

const getCoverUrl = (coverUrl?: string | null) => getStaticUrl(coverUrl) ?? ''

const getFileExtension = (fileName: string) => {
  const ext = fileName.includes('.') ? fileName.slice(fileName.lastIndexOf('.')) : ''
  return ext.toLowerCase()
}

const loadBooks = async () => {
  isLoading.value = true
  try {
    books.value = await getBooks(0, 200)
  } catch (error) {
    const message = error instanceof Error ? error.message : '获取图书列表失败'
    toast.error(message)
  } finally {
    isLoading.value = false
  }
}

const openImportPicker = () => {
  if (isImporting.value) return
  fileInput.value?.click()
}

const handleFileChange = async (event: Event) => {
  const input = event.target as HTMLInputElement
  const selectedFile = input.files?.[0]
  input.value = ''
  if (!selectedFile) return

  const ext = getFileExtension(selectedFile.name)
  if (!allowedExtensions.has(ext)) {
    toast.error('暂不支持该文件格式，请选择 EPUB、PDF、MOBI、AZW/AZW3 或 TXT 文件。')
    return
  }

  if (selectedFile.size > MAX_BOOK_FILE_SIZE) {
    toast.error('图书文件过大，当前仅支持 200MB 以内的文件。')
    return
  }

  isImporting.value = true
  try {
    const imported = await importBook(selectedFile)
    books.value = [imported, ...books.value.filter(book => book.id !== imported.id)]
    toast.success(`《${imported.title}》已导入图书馆`)
  } catch (error) {
    const message = error instanceof Error ? error.message : '导入图书失败'
    toast.error(message)
  } finally {
    isImporting.value = false
  }
}

onMounted(() => {
  void loadBooks()
})
</script>

<template>
  <div class="book-library-home">
    <header class="library-header" @dblclick="handleToggleMaximize" @contextmenu="handleHeaderContextMenu">
      <div class="library-header-inner">
        <div class="library-title-row">
          <div class="library-title">
            <button class="back-btn" @click="emit('back-chat')">返回</button>
            <BookOpen :size="18" />
            <span>与作者共读</span>
          </div>
          <div class="header-actions">
            <button class="ghost-action" :disabled="isLoading || isImporting" @click="loadBooks">
              <RefreshCw :size="14" :class="{ spinning: isLoading }" />
              刷新列表
            </button>
            <button class="primary-action" :disabled="isImporting" @click="openImportPicker">
              <LoaderCircle v-if="isImporting" :size="14" class="spinning" />
              <FilePlus2 v-else :size="14" />
              {{ isImporting ? '导入中...' : '导入图书' }}
            </button>
            <input
              ref="fileInput"
              class="hidden-file-input"
              type="file"
              :accept="accept"
              @change="handleFileChange">
          </div>
        </div>
      </div>
    </header>

    <section class="workspace-grid">
      <article class="shelf-panel">
        <div class="panel-header">
          <div>
            <div class="panel-title">我的图书馆</div>
          </div>
          <span class="panel-badge">{{ totalBooks ? `共 ${totalBooks} 本` : '等待导入' }}</span>
        </div>

        <div v-if="isLoading" class="loading-shelf">
          <LoaderCircle :size="22" class="spinning" />
          <span>正在加载图书列表...</span>
        </div>

        <div v-else-if="!books.length" class="empty-shelf">
          <div class="shelf-illustration" aria-hidden="true">
            <span class="book-spine spine-green"></span>
            <span class="book-spine spine-dark"></span>
            <span class="book-spine spine-light"></span>
            <span class="book-spine spine-soft"></span>
          </div>
          <h2>图书馆里还没有书</h2>
          <p>先导入一本 EPUB、PDF、MOBI、AZW/AZW3 或 TXT 文件。导入后系统会把文件复制到默认图书馆文件夹，并尽量提取基础信息。</p>
          <button class="empty-import-action" :disabled="isImporting" @click="openImportPicker">
            <LoaderCircle v-if="isImporting" :size="16" class="spinning" />
            <FilePlus2 v-else :size="16" />
            {{ isImporting ? '导入中...' : '导入第一本书' }}
          </button>
        </div>

        <div v-else class="book-grid">
          <article v-for="book in books" :key="book.id" class="book-card">
            <div class="book-cover-shell">
              <img
                v-if="getCoverUrl(book.cover_url)"
                :src="getCoverUrl(book.cover_url)"
                :alt="`${book.title} 封面`"
                class="book-cover"
                loading="lazy">
              <div v-else class="book-cover-placeholder">
                <span class="cover-format">{{ getFormatLabel(book.format_type) }}</span>
                <span class="cover-title">{{ book.title }}</span>
              </div>
              <span class="status-pill" :class="`status-${book.status}`">{{ getStatusLabel(book.status) }}</span>
            </div>

            <div class="book-meta">
              <h3>{{ book.title }}</h3>
              <p class="book-author">{{ book.author || '作者待识别' }}</p>
            </div>
          </article>
        </div>
      </article>
    </section>
  </div>
</template>

<style scoped>
.book-library-home {
  position: relative;
  isolation: isolate;
  display: flex;
  flex-direction: column;
  min-height: 100%;
  background:
    radial-gradient(circle at top left, rgba(7, 193, 96, 0.1), transparent 28%),
    radial-gradient(circle at 92% 18%, rgba(23, 23, 23, 0.06), transparent 24%),
    linear-gradient(180deg, #f7f8f7 0%, #eef2ef 52%, #f3f4f3 100%);
  overflow: auto;
}

.book-library-home::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.48) 0%, transparent 32%),
    linear-gradient(225deg, rgba(7, 193, 96, 0.04) 0%, transparent 28%);
  pointer-events: none;
}

.book-library-home > * {
  position: relative;
  z-index: 1;
}

.library-header {
  padding: 20px 130px 14px 24px;
  border-bottom: 1px solid rgba(214, 220, 214, 0.95);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.9) 0%, rgba(246, 248, 246, 0.94) 100%);
  box-shadow: 0 10px 24px rgba(31, 41, 31, 0.05);
}

.library-header-inner {
  -webkit-app-region: drag;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.library-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.library-title {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #1f2937;
  font-size: 18px;
  font-weight: 600;
}

.back-btn,
.ghost-action,
.primary-action,
.empty-import-action {
  -webkit-app-region: no-drag;
}

.back-btn {
  display: none;
  border: none;
  background: transparent;
  color: #07c160;
  font-size: 12px;
  padding: 4px 6px;
  border-radius: 6px;
  cursor: pointer;
}

.back-btn:hover {
  background: rgba(7, 193, 96, 0.1);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.ghost-action,
.primary-action,
.empty-import-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border: none;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 600;
  transition: transform 0.18s ease, box-shadow 0.18s ease, opacity 0.18s ease;
  cursor: pointer;
}

.ghost-action {
  min-width: 102px;
  height: 36px;
  padding: 0 14px;
  border: 1px solid rgba(202, 210, 202, 0.9);
  background: rgba(255, 255, 255, 0.84);
  color: #5f6b63;
}

.ghost-action:hover:not(:disabled),
.primary-action:hover:not(:disabled),
.empty-import-action:hover:not(:disabled) {
  transform: translateY(-1px);
}

.primary-action,
.empty-import-action {
  background: linear-gradient(135deg, #07c160 0%, #10a04e 100%);
  color: #fff;
}

.primary-action {
  min-width: 116px;
  height: 36px;
  padding: 0 16px;
  box-shadow: 0 12px 24px rgba(7, 193, 96, 0.18);
}

.empty-import-action {
  width: 100%;
  height: 42px;
}

.ghost-action:disabled,
.primary-action:disabled,
.empty-import-action:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.hidden-file-input {
  display: none;
}

.workspace-grid {
  padding-left: 24px;
  padding-right: 24px;
}

.shelf-panel {
  border: 1px solid rgba(217, 224, 217, 0.96);
  background: rgba(255, 255, 255, 0.8);
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.05);
  backdrop-filter: blur(16px);
}

.workspace-grid {
  padding-top: 18px;
  padding-bottom: 18px;
}

.shelf-panel {
  border-radius: 28px;
}

.shelf-panel {
  padding: 24px;
}

.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
}

.panel-title {
  color: #1f2937;
  font-size: 16px;
  font-weight: 600;
}

.panel-subtitle {
  margin-top: 8px;
  color: #6b7280;
  font-size: 13px;
  line-height: 1.7;
  max-width: 62ch;
}

.panel-badge {
  flex-shrink: 0;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(243, 244, 246, 0.9);
  color: #6b7280;
  font-size: 11px;
  font-weight: 600;
}

.loading-shelf,
.empty-shelf {
  margin-top: 22px;
  min-height: 360px;
  border-radius: 24px;
  border: 1px dashed rgba(189, 199, 189, 0.95);
  background:
    linear-gradient(180deg, rgba(248, 250, 248, 0.9) 0%, rgba(240, 244, 240, 0.95) 100%);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 24px;
  text-align: center;
}

.loading-shelf {
  gap: 10px;
  color: #5f6b63;
  font-size: 14px;
}

.shelf-illustration {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  height: 92px;
  padding: 0 18px 18px;
  border-bottom: 3px solid rgba(157, 176, 157, 0.85);
}

.book-spine {
  display: inline-flex;
  width: 28px;
  border-radius: 8px 8px 2px 2px;
  box-shadow: 0 12px 22px rgba(15, 23, 42, 0.1);
}

.spine-green {
  height: 74px;
  background: linear-gradient(180deg, #22c55e 0%, #14924a 100%);
}

.spine-dark {
  height: 58px;
  background: linear-gradient(180deg, #475569 0%, #293241 100%);
}

.spine-light {
  height: 68px;
  background: linear-gradient(180deg, #d9f99d 0%, #84cc16 100%);
}

.spine-soft {
  height: 50px;
  background: linear-gradient(180deg, #e5e7eb 0%, #cbd5e1 100%);
}

.empty-shelf h2 {
  margin-top: 28px;
  color: #1f2937;
  font-size: 24px;
  font-weight: 700;
}

.empty-shelf p {
  margin-top: 12px;
  max-width: 58ch;
  color: #6b7280;
  font-size: 14px;
  line-height: 1.8;
}

.empty-import-action {
  max-width: 220px;
  margin-top: 20px;
}

.book-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
  margin-top: 22px;
}

.book-card {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 16px;
  border-radius: 22px;
  background: linear-gradient(180deg, rgba(248, 250, 248, 0.98) 0%, rgba(241, 245, 241, 0.98) 100%);
  border: 1px solid rgba(221, 228, 221, 0.98);
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.05);
}

.book-cover-shell {
  position: relative;
  width: 100%;
  aspect-ratio: 3 / 4;
  border-radius: 18px;
  overflow: hidden;
  background: linear-gradient(180deg, #e6ece6 0%, #dce4dc 100%);
}

.book-cover {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.book-cover-placeholder {
  width: 100%;
  height: 100%;
  padding: 16px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  background:
    linear-gradient(145deg, rgba(7, 193, 96, 0.9) 0%, rgba(9, 161, 84, 0.92) 100%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.08), rgba(255, 255, 255, 0));
  color: #fff;
}

.cover-format {
  align-self: flex-start;
  padding: 4px 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.16);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.cover-title {
  font-size: 18px;
  font-weight: 700;
  line-height: 1.35;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.status-pill {
  position: absolute;
  top: 12px;
  right: 12px;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.92);
  color: #1f2937;
  font-size: 11px;
  font-weight: 700;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.12);
}

.status-imported {
  color: #03874d;
}

.status-failed {
  color: #b91c1c;
}

.status-limited {
  color: #b45309;
}

.book-meta h3 {
  color: #1f2937;
  font-size: 16px;
  font-weight: 700;
  line-height: 1.5;
}

.book-author,
.book-status-detail {
  margin-top: 6px;
  color: #6b7280;
  font-size: 12px;
  line-height: 1.7;
}

.spinning {
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 767px) {
  .library-header,
  .workspace-grid {
    padding-left: 16px;
    padding-right: 16px;
  }

  .library-header {
    padding-top: 16px;
    padding-right: 16px;
  }

  .library-title-row,
  .panel-header {
    flex-direction: column;
    align-items: stretch;
  }

  .header-actions {
    width: 100%;
    flex-wrap: wrap;
  }

  .ghost-action,
  .primary-action {
    flex: 1;
  }

  .back-btn {
    display: inline-flex;
    align-items: center;
  }

  .shelf-panel {
    border-radius: 22px;
  }

  .loading-shelf,
  .empty-shelf {
    min-height: 300px;
    padding: 20px 16px;
  }

  .empty-shelf h2 {
    font-size: 21px;
  }

  .book-grid {
    grid-template-columns: 1fr;
  }
}
</style>
