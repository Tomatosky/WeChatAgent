<script setup lang="ts">
import { computed } from 'vue'
import { ChevronRight } from 'lucide-vue-next'

import type { TocItem } from '@/lib/book-reader/readerAdapter'

defineOptions({
  name: 'ReaderTocTree',
})

const props = withDefaults(
  defineProps<{
    items: TocItem[]
    level?: number
    activeLabel?: string
  }>(),
  {
    level: 0,
    activeLabel: '',
  },
)

const emit = defineEmits<{
  (e: 'select', item: TocItem): void
}>()

const indentStyle = computed(() => ({
  '--toc-indent': `${props.level * 14}px`,
}))
</script>

<template>
  <ul class="toc-tree" :style="indentStyle">
    <li v-for="(item, index) in items" :key="`${item.target ?? item.label}-${level}-${index}`" class="toc-node">
      <button
        type="button"
        class="toc-node-btn"
        :class="{
          active: item.label === activeLabel && !item.disabled,
          disabled: item.disabled,
        }"
        :disabled="item.disabled"
        @click="emit('select', item)"
      >
        <span class="toc-node-prefix">
          <ChevronRight v-if="item.children.length" :size="14" />
          <span v-else class="toc-node-dot" />
        </span>
        <span class="toc-node-label">{{ item.label }}</span>
      </button>

      <ReaderTocTree
        v-if="item.children.length"
        :items="item.children"
        :level="level + 1"
        :active-label="activeLabel"
        @select="emit('select', $event)"
      />
    </li>
  </ul>
</template>

<style scoped>
.toc-tree {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.toc-node {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.toc-node-btn {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  width: 100%;
  padding: 10px 12px 10px calc(12px + var(--toc-indent));
  border: none;
  border-radius: 12px;
  background: transparent;
  color: #334155;
  text-align: left;
  cursor: pointer;
  transition: background-color 0.2s ease, color 0.2s ease;
}

.toc-node-btn:hover:not(:disabled) {
  background: rgba(7, 193, 96, 0.08);
  color: #087443;
}

.toc-node-btn.active {
  background: rgba(7, 193, 96, 0.12);
  color: #087443;
}

.toc-node-btn.disabled {
  opacity: 0.56;
  cursor: not-allowed;
}

.toc-node-prefix {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 14px;
  margin-top: 2px;
  color: #94a3b8;
}

.toc-node-dot {
  width: 5px;
  height: 5px;
  border-radius: 999px;
  background: currentColor;
}

.toc-node-label {
  flex: 1;
  min-width: 0;
  font-size: 13px;
  line-height: 1.65;
  word-break: break-word;
}
</style>
