<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import {
  BookOpen,
  Ellipsis,
  FilePlus2,
  LoaderCircle,
  RefreshCw,
  Trash2,
  UserRound,
} from 'lucide-vue-next'

import { getStaticUrl } from '@/api/base'
import {
  deleteBook,
  getBooks,
  importBook,
  updateBook,
  type Book,
} from '@/api/book'
import { getFriends, type Friend } from '@/api/friend'
import { useToast } from '@/composables/useToast'

const emit = defineEmits<{
  (e: 'back-chat'): void
  (e: 'open-reader', book: Book): void
}>()

const toast = useToast()
const isElectron = Boolean(window.WeAgentChat?.windowControls)
const fileInput = ref<HTMLInputElement | null>(null)
const books = ref<Book[]>([])
const friends = ref<Friend[]>([])
const isLoading = ref(false)
const isImporting = ref(false)
const editingBookId = ref<number | null>(null)
const savingBookId = ref<number | null>(null)
const deletingBookId = ref<number | null>(null)
const menuOpenBookId = ref<number | null>(null)
const pendingDeleteBook = ref<Book | null>(null)

const toggleMenu = (bookId: number, event: Event) => {
  event.stopPropagation()
  menuOpenBookId.value = menuOpenBookId.value === bookId ? null : bookId
}

const closeAllMenus = () => {
  menuOpenBookId.value = null
}

const editForm = reactive({
  aiFriendId: '',
})

const MAX_BOOK_FILE_SIZE = 200 * 1024 * 1024
const accept = '.epub,.pdf,.mobi,.azw,.azw3,.txt'
const allowedExtensions = new Set(['.epub', '.pdf', '.mobi', '.azw', '.azw3', '.txt'])

const totalBooks = computed(() => books.value.length)
const bindableFriends = computed(() => friends.value.filter(friend => !friend.deleted))

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


const getFormatLabel = (formatType: string) => formatType.toUpperCase()

const getCoverUrl = (coverUrl?: string | null) => getStaticUrl(coverUrl) ?? ''

const getFileExtension = (fileName: string) => {
  const ext = fileName.includes('.') ? fileName.slice(fileName.lastIndexOf('.')) : ''
  return ext.toLowerCase()
}

const getBindingLabel = (book: Book) => {
  if (book.author_binding_status === 'valid') {
    return book.bound_friend_name || '已绑定作者'
  }
  if (book.author_binding_status === 'invalid') {
    return '作者失效'
  }
  return '未绑定作者'
}

const replaceBookInList = (nextBook: Book) => {
  books.value = books.value.map(book => (book.id === nextBook.id ? nextBook : book))
}

const openBookReader = (book: Book) => {
  if (editingBookId.value === book.id) return
  closeAllMenus()
  emit('open-reader', book)
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

const loadFriends = async () => {
  try {
    friends.value = await getFriends(0, 300)
  } catch (error) {
    console.error('加载好友列表失败', error)
    toast.error('加载作者列表失败')
  }
}

const loadInitialData = async () => {
  await Promise.all([loadBooks(), loadFriends()])
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

const startEditing = (book: Book) => {
  editingBookId.value = book.id
  editForm.aiFriendId = book.ai_friend_id == null ? '' : String(book.ai_friend_id)
}

const cancelEditing = () => {
  editingBookId.value = null
  editForm.aiFriendId = ''
}

const handleSaveBook = async () => {
  if (editingBookId.value == null) return

  savingBookId.value = editingBookId.value
  try {
    const updated = await updateBook(editingBookId.value, {
      ai_friend_id: editForm.aiFriendId ? Number(editForm.aiFriendId) : null,
    })
    replaceBookInList(updated)
    cancelEditing()
    toast.success(`《${updated.title}》作者绑定已更新`)
  } catch (error) {
    const message = error instanceof Error ? error.message : '更新图书失败'
    toast.error(message)
  } finally {
    savingBookId.value = null
  }
}

const handleDeleteBook = async (book: Book) => {
  closeAllMenus()
  deletingBookId.value = book.id
  try {
    await deleteBook(book.id)
    books.value = books.value.filter(item => item.id !== book.id)
    if (editingBookId.value === book.id) {
      cancelEditing()
    }
    toast.success(`《${book.title}》已删除`)
  } catch (error) {
    const message = error instanceof Error ? error.message : '删除图书失败'
    toast.error(message)
  } finally {
    deletingBookId.value = null
  }
}

const handleDeleteAction = async (book: Book, event: Event) => {
  event.preventDefault()
  event.stopPropagation()
  closeAllMenus()
  pendingDeleteBook.value = book
}

const cancelDelete = () => {
  pendingDeleteBook.value = null
}

const confirmDelete = async () => {
  if (!pendingDeleteBook.value) return
  const target = pendingDeleteBook.value
  pendingDeleteBook.value = null
  await handleDeleteBook(target)
}

onMounted(() => {
  void loadInitialData()
  document.addEventListener('click', closeAllMenus)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', closeAllMenus)
})
</script>

<template>
  <div class="book-library-home">
    <div v-if="pendingDeleteBook" class="confirm-mask" @click="cancelDelete">
      <div class="confirm-dialog" @click.stop>
        <h3 class="confirm-title">删除图书</h3>
        <p class="confirm-text">确认删除《{{ pendingDeleteBook.title }}》吗？删除后无法恢复。</p>
        <div class="confirm-actions">
          <button class="btn-ghost btn-sm" @click="cancelDelete">取消</button>
          <button class="btn-danger btn-sm" :disabled="deletingBookId === pendingDeleteBook.id" @click="confirmDelete">
            <LoaderCircle v-if="deletingBookId === pendingDeleteBook.id" :size="12" class="spinning" />
            <Trash2 v-else :size="12" />
            <span>确认删除</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Header -->
    <header 
      class="lib-header"
      @dblclick="handleToggleMaximize" 
      @contextmenu="handleHeaderContextMenu"
    >
      <div class="lib-header-inner">
        <div class="lib-title-group">
          <button class="back-btn" @click="emit('back-chat')" title="返回">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6"/></svg>
          </button>
          <div class="lib-icon">
            <BookOpen :size="18" />
          </div>
          <span class="lib-title-text">与作者共读</span>
        </div>
        <div class="lib-actions">
          <button class="btn-ghost" :disabled="isLoading || isImporting" @click="loadInitialData">
            <RefreshCw :size="14" :class="{ spinning: isLoading }" />
            刷新列表
          </button>
          <button class="btn-primary" :disabled="isImporting" @click="openImportPicker">
            <LoaderCircle v-if="isImporting" :size="14" class="spinning" />
            <FilePlus2 v-else :size="14" />
            {{ isImporting ? '导入中...' : '导入图书' }}
          </button>
          <input ref="fileInput" type="file" :accept="accept" class="sr-only" @change="handleFileChange">
        </div>
      </div>
    </header>

    <!-- Main Scroll Area -->
    <main class="lib-main">
      <div class="shelf-card">
        <!-- Shelf Header -->
        <div class="shelf-header">
          <h2 class="shelf-title">我的图书馆</h2>
          <span class="shelf-badge">{{ totalBooks ? `共 ${totalBooks} 本` : '等待导入' }}</span>
        </div>

        <!-- Loading -->
        <div v-if="isLoading" class="empty-state">
          <LoaderCircle :size="24" class="spinning text-green" />
          <p>正在加载图书列表...</p>
        </div>

        <!-- Empty -->
        <div v-else-if="!books.length" class="empty-state">
          <div class="empty-icon-wrap">
            <BookOpen :size="28" />
          </div>
          <h3>图书馆里还没有书</h3>
          <p class="empty-hint">导入一本书后，就可以绑定 AI 作者，开启深度阅读对谈体验。</p>
          <button class="btn-primary" :disabled="isImporting" @click="openImportPicker">
            <LoaderCircle v-if="isImporting" :size="14" class="spinning" />
            <FilePlus2 v-else :size="14" />
            {{ isImporting ? '导入中...' : '导入第一本书' }}
          </button>
        </div>

        <!-- Book Grid -->
        <div v-else class="book-grid">
          <article v-for="book in books" :key="book.id" class="book-card" @click="openBookReader(book)">
            <!-- Cover -->
            <div class="cover-wrap">
              <img
                v-if="getCoverUrl(book.cover_url)"
                :src="getCoverUrl(book.cover_url)"
                :alt="`${book.title} 封面`"
                class="cover-img"
                loading="lazy"
              >
              <div v-else class="cover-placeholder">
                <span class="cover-format-tag">{{ getFormatLabel(book.format_type) }}</span>
                <span class="cover-title-text">{{ book.title }}</span>
              </div>
              <!-- More Menu Button -->
              <div class="cover-menu-anchor">
                <button class="cover-menu-btn" @click="toggleMenu(book.id, $event)" title="更多操作">
                  <Ellipsis :size="16" />
                </button>
                <div v-if="menuOpenBookId === book.id" class="cover-dropdown" @click.stop>
                  <button
                    type="button"
                    class="dropdown-item dropdown-item-danger"
                    :disabled="deletingBookId === book.id"
                    @click="handleDeleteAction(book, $event)"
                  >
                    <LoaderCircle v-if="deletingBookId === book.id" :size="14" class="spinning" />
                    <Trash2 v-else :size="14" />
                    <span>删除图书</span>
                  </button>
                </div>
              </div>
            </div>

            <!-- Meta -->
            <div class="book-meta">
              <h3 class="book-title">{{ book.title }}</h3>
              <p class="book-author">{{ book.author || '原作者待补充' }}</p>
              <button type="button" class="binding-btn" :class="'bind-' + book.author_binding_status" @click.stop="startEditing(book)">
                <UserRound :size="12" />
                <span>{{ getBindingLabel(book) }}</span>
              </button>
            </div>

            <!-- Edit Overlay -->
            <div v-if="editingBookId === book.id" class="edit-overlay" @click.stop>
              <label class="edit-label">绑定 AI 作者</label>
              <select v-model="editForm.aiFriendId" class="edit-select">
                <option value="">暂不绑定</option>
                <option v-for="friend in bindableFriends" :key="friend.id" :value="String(friend.id)">{{ friend.name }}</option>
              </select>
              <button class="btn-primary btn-sm" :disabled="savingBookId === book.id" @click="handleSaveBook">
                <LoaderCircle v-if="savingBookId === book.id" :size="12" class="spinning" />
                <span>{{ savingBookId === book.id ? '保存...' : '确认绑定' }}</span>
              </button>
              <button class="btn-ghost btn-sm" style="width:100%" @click="cancelEditing">取消</button>
            </div>
          </article>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
/* ── Root ── */
.book-library-home {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  background: linear-gradient(180deg, #f7f8fa 0%, #eef1f0 100%);
  overflow: hidden;
}

/* ── Header ── */
.lib-header {
  flex: none;
  padding: 14px 24px 12px;
  border-bottom: 1px solid rgba(0,0,0,0.06);
  background: rgba(255,255,255,0.82);
  backdrop-filter: blur(18px);
  -webkit-app-region: drag;
}
.lib-header-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.lib-title-group {
  display: flex;
  align-items: center;
  gap: 10px;
}
.back-btn {
  display: none;
  -webkit-app-region: no-drag;
  border: none;
  background: transparent;
  color: #07c160;
  padding: 4px;
  border-radius: 8px;
  cursor: pointer;
}
.back-btn:hover { background: rgba(7,193,96,0.08); }
.lib-icon {
  width: 34px;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  background: #07c160;
  color: #fff;
}
.lib-title-text {
  font-size: 17px;
  font-weight: 700;
  color: #1e293b;
}
.lib-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  -webkit-app-region: no-drag;
}

/* ── Buttons ── */
.btn-ghost, .btn-primary, .btn-danger {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  border: none;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  -webkit-app-region: no-drag;
}
.btn-ghost {
  height: 34px;
  padding: 0 14px;
  background: #fff;
  border: 1px solid #e2e8f0;
  color: #64748b;
}
.btn-ghost:hover:not(:disabled) { border-color: #cbd5e1; color: #334155; box-shadow: 0 2px 8px rgba(0,0,0,0.04); }
.btn-primary {
  height: 34px;
  padding: 0 16px;
  background: #07c160;
  color: #fff;
  box-shadow: 0 4px 12px rgba(7,193,96,0.2);
}
.btn-primary:hover:not(:disabled) { background: #06ad56; box-shadow: 0 6px 16px rgba(7,193,96,0.28); }
.btn-danger {
  height: 30px;
  padding: 0 10px;
  background: #fef2f2;
  color: #dc2626;
  border: 1px solid #fecaca;
}
.btn-danger:hover:not(:disabled) { background: #dc2626; color: #fff; border-color: #dc2626; }
.btn-sm { height: 30px; font-size: 12px; padding: 0 12px; }
.btn-ghost:disabled, .btn-primary:disabled, .btn-danger:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0,0,0,0); }

.confirm-mask {
  position: fixed;
  inset: 0;
  z-index: 120;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: rgba(15, 23, 42, 0.28);
  backdrop-filter: blur(4px);
}

.confirm-dialog {
  width: min(320px, 100%);
  padding: 18px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.98);
  border: 1px solid #e2e8f0;
  box-shadow: 0 18px 48px rgba(15, 23, 42, 0.16);
}

.confirm-title {
  font-size: 16px;
  font-weight: 700;
  color: #1e293b;
}

.confirm-text {
  margin-top: 8px;
  font-size: 13px;
  line-height: 1.6;
  color: #64748b;
}

.confirm-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 16px;
}

/* ── Main ── */
.lib-main {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
}
.lib-main::-webkit-scrollbar { width: 5px; }
.lib-main::-webkit-scrollbar-track { background: transparent; }
.lib-main::-webkit-scrollbar-thumb { background: rgba(0,0,0,0.12); border-radius: 10px; }

/* ── Shelf Card ── */
.shelf-card {
  background: rgba(255,255,255,0.72);
  border: 1px solid rgba(255,255,255,0.9);
  border-radius: 20px;
  padding: 20px 24px;
  backdrop-filter: blur(12px);
  box-shadow: 0 6px 24px rgba(0,0,0,0.03);
}
.shelf-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.shelf-title {
  font-size: 15px;
  font-weight: 700;
  color: #1e293b;
}
.shelf-badge {
  font-size: 11px;
  font-weight: 600;
  color: #94a3b8;
  padding: 4px 10px;
  border-radius: 999px;
  background: #f1f5f9;
}

/* ── Empty / Loading ── */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  gap: 8px;
  color: #94a3b8;
  font-size: 14px;
  text-align: center;
}
.empty-state h3 { color: #1e293b; font-size: 18px; font-weight: 700; }
.empty-hint { max-width: 280px; font-size: 13px; line-height: 1.6; color: #94a3b8; margin-bottom: 12px; }
.empty-icon-wrap {
  width: 56px;
  height: 56px;
  border-radius: 16px;
  background: rgba(7,193,96,0.08);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #07c160;
  margin-bottom: 8px;
}
.text-green { color: #07c160; }

/* ── Book Grid ── */
.book-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 16px;
}

/* ── Book Card ── */
.book-card {
  position: relative;
  display: flex;
  flex-direction: column;
  background: #fff;
  border: 1px solid #f1f5f9;
  border-radius: 14px;
  padding: 10px;
  cursor: pointer;
  transition: transform 0.25s, box-shadow 0.25s;
}
.book-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 24px rgba(0,0,0,0.07);
}

/* ── Cover ── */
.cover-wrap {
  position: relative;
  width: 100%;
  height: 200px;
  border-radius: 10px;
  background: #f1f5f9;
}
.cover-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: transform 0.5s;
  border-radius: 10px;
}
.book-card:hover .cover-img { transform: scale(1.03); }
.cover-placeholder {
  width: 100%;
  height: 100%;
  padding: 12px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  background: linear-gradient(145deg, rgba(7,193,96,0.85) 0%, rgba(5,140,70,0.9) 100%);
  color: #fff;
  border-radius: 10px;
}
.cover-format-tag {
  align-self: flex-start;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.06em;
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(255,255,255,0.2);
}
.cover-title-text {
  font-size: 14px;
  font-weight: 700;
  line-height: 1.3;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* ── Cover Menu ── */
.cover-menu-anchor {
  position: absolute;
  top: 6px;
  right: 6px;
  z-index: 10;
}
.cover-menu-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 8px;
  border: none;
  background: rgba(255,255,255,0.85);
  backdrop-filter: blur(8px);
  color: #64748b;
  cursor: pointer;
  box-shadow: 0 2px 6px rgba(0,0,0,0.1);
  transition: all 0.2s;
  opacity: 0;
}
.book-card:hover .cover-menu-btn { opacity: 1; }
.cover-menu-btn:hover {
  background: rgba(255,255,255,0.95);
  color: #1e293b;
  box-shadow: 0 4px 10px rgba(0,0,0,0.14);
}
.cover-dropdown {
  position: absolute;
  top: calc(100% + 4px);
  right: 0;
  min-width: 120px;
  padding: 4px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.12);
  animation: fadeIn 0.15s ease-out;
}
.dropdown-item {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding: 8px 10px;
  border: none;
  border-radius: 7px;
  background: transparent;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
}
.dropdown-item-danger {
  color: #dc2626;
}
.dropdown-item-danger:hover {
  background: #fef2f2;
}
.dropdown-item:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ── Meta ── */
.book-meta {
  display: flex;
  flex-direction: column;
  flex: 1;
  padding: 8px 2px 2px;
}
.book-title {
  font-size: 13px;
  font-weight: 700;
  color: #1e293b;
  line-height: 1.4;
  min-height: calc(2 * 1.4em); /* always reserve 2 lines */
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.book-card:hover .book-title { color: #07c160; }
.book-author {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ── Binding Button ── */
.binding-btn {
  margin-top: auto;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 5px 8px;
  border-radius: 8px;
  border: none;
  cursor: pointer;
  font-size: 11px;
  font-weight: 600;
  transition: all 0.2s;
}
.bind-valid { color: #16a34a; background: rgba(34,197,94,0.08); }
.bind-valid:hover { background: rgba(34,197,94,0.15); }
.bind-invalid { color: #dc2626; background: rgba(248,113,113,0.1); }
.bind-invalid:hover { background: rgba(248,113,113,0.18); }
.bind-unbound { color: #64748b; background: #f1f5f9; }
.bind-unbound:hover { background: #e2e8f0; }

/* ── Edit Overlay ── */
.edit-overlay {
  position: absolute;
  inset: 0;
  z-index: 20;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px;
  background: rgba(255,255,255,0.96);
  backdrop-filter: blur(16px);
  border-radius: 14px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 8px 28px rgba(0,0,0,0.1);
  justify-content: center;
  animation: fadeIn 0.2s ease-out;
}
.edit-label {
  font-size: 11px;
  font-weight: 700;
  color: #475569;
}
.edit-select {
  width: 100%;
  height: 34px;
  padding: 0 10px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  font-size: 12px;
  color: #334155;
  outline: none;
  -webkit-app-region: no-drag;
  cursor: pointer;
}
.edit-select:focus { border-color: #07c160; box-shadow: 0 0 0 2px rgba(7,193,96,0.12); }
.edit-row {
  display: flex;
  gap: 6px;
}
.edit-row .btn-ghost, .edit-row .btn-danger { flex: 1; }

/* ── Animations ── */
@keyframes fadeIn {
  from { opacity: 0; transform: scale(0.96); }
  to { opacity: 1; transform: scale(1); }
}
.spinning {
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ── Responsive ── */
@media (max-width: 767px) {
  .lib-header { padding: 12px 16px; }
  .lib-main { padding: 16px; }
  .lib-title-group .back-btn { display: flex; }
  .lib-header-inner { flex-direction: column; gap: 10px; align-items: stretch; }
  .lib-actions { width: 100%; }
  .lib-actions .btn-ghost, .lib-actions .btn-primary { flex: 1; }
  .book-grid { grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: 12px; }
  .shelf-card { padding: 16px; border-radius: 16px; }
}
</style>
