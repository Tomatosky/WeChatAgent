<script setup lang="ts">
import { BookOpen, ListTree, X } from 'lucide-vue-next'

import type { TocItem } from '@/lib/book-reader/readerAdapter'
import ReaderTocTree from './ReaderTocTree.vue'

defineProps<{
  open: boolean
  items: TocItem[]
  activeLabel?: string
}>()

const emit = defineEmits<{
  (e: 'update:open', value: boolean): void
  (e: 'select', item: TocItem): void
}>()

const closePanel = () => emit('update:open', false)
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="toc-layer">
      <button type="button" class="toc-backdrop" aria-label="关闭目录抽屉" @click="closePanel" />

      <aside class="toc-panel" aria-label="阅读目录">
        <header class="toc-header">
          <div class="toc-header-title">
            <div class="toc-header-icon">
              <ListTree :size="16" />
            </div>
            <div>
              <p class="toc-eyebrow">阅读导航</p>
              <h2>目录</h2>
            </div>
          </div>

          <button type="button" class="toc-close-btn" @click="closePanel">
            <X :size="16" />
          </button>
        </header>

        <div v-if="items.length" class="toc-body">
          <ReaderTocTree :items="items" :active-label="activeLabel" @select="emit('select', $event)" />
        </div>

        <div v-else class="toc-empty">
          <div class="toc-empty-icon">
            <BookOpen :size="18" />
          </div>
          <h3>该文件无可用目录</h3>
          <p>这本书当前没有可解析的章节结构，你仍然可以继续按翻页或滚动方式阅读。</p>
        </div>
      </aside>
    </div>
  </Teleport>
</template>

<style scoped>
.toc-layer {
  position: fixed;
  inset: 0;
  z-index: 1200;
}

.toc-backdrop {
  position: absolute;
  inset: 0;
  border: none;
  background: rgba(15, 23, 42, 0.3);
  backdrop-filter: blur(4px);
  cursor: pointer;
}

.toc-panel {
  position: absolute;
  top: 0;
  right: 0;
  display: flex;
  flex-direction: column;
  width: min(380px, 92vw);
  height: 100%;
  padding: 18px 16px 16px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(247, 243, 234, 0.98) 100%);
  border-left: 1px solid rgba(148, 163, 184, 0.18);
  box-shadow: -20px 0 48px rgba(15, 23, 42, 0.16);
}

.toc-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 14px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.16);
}

.toc-header-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.toc-header-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 12px;
  background: rgba(7, 193, 96, 0.12);
  color: #087443;
}

.toc-eyebrow {
  margin: 0;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #07c160;
}

.toc-header h2 {
  margin: 3px 0 0;
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
}

.toc-close-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.92);
  color: #475569;
  cursor: pointer;
  transition: border-color 0.2s ease, color 0.2s ease;
}

.toc-close-btn:hover {
  color: #0f172a;
  border-color: rgba(100, 116, 139, 0.28);
}

.toc-body {
  flex: 1;
  overflow-y: auto;
  padding-top: 14px;
}

.toc-body::-webkit-scrollbar {
  width: 6px;
}

.toc-body::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.32);
}

.toc-empty {
  display: flex;
  flex: 1;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 24px;
  text-align: center;
}

.toc-empty-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border-radius: 14px;
  background: rgba(148, 163, 184, 0.12);
  color: #64748b;
}

.toc-empty h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
}

.toc-empty p {
  margin: 0;
  max-width: 260px;
  font-size: 13px;
  line-height: 1.7;
  color: #64748b;
}

@media (max-width: 640px) {
  .toc-panel {
    width: 100vw;
    padding-left: 14px;
    padding-right: 14px;
  }
}
</style>
