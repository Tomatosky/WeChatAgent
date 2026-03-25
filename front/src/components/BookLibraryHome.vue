<script setup lang="ts">
import {
  BookOpen,
  Import,
  MessagesSquare,
  Sparkles,
  Library,
  BookmarkCheck,
  ArrowRight,
} from 'lucide-vue-next'

const emit = defineEmits<{
  (e: 'back-chat'): void
}>()

const isElectron = Boolean(window.WeAgentChat?.windowControls)

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

const capabilities = [
  {
    title: '图书导入',
    description: '后续会在这里接入 EPUB、PDF、TXT 等格式的文件导入入口与处理状态。',
    icon: Import,
  },
  {
    title: '作者绑定',
    description: '每本书都可以绑定已有 AI 好友，后续阅读和伴读聊天会按书籍维度隔离。',
    icon: Sparkles,
  },
  {
    title: '伴读聊天',
    description: '阅读器与聊天侧栏会在后续 Story 接入，这里先把一级导航和页面容器稳定下来。',
    icon: MessagesSquare,
  },
] as const

const deliveryNotes = [
  '导航方案：沿用现有单页主视图切换，不新增路由。',
  '恢复策略：刷新或重开应用后，恢复最近一次一级入口；非法值回落到聊天页。',
  '本 Story 仅交付入口与基础界面，不接入图书 CRUD、导入解析或阅读器。',
] as const

const statusStages = ['imported', 'processing', 'ready', 'limited', 'failed'] as const
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
            <span class="phase-pill">主界面入口已接入</span>
          </div>
          <div class="header-actions">
            <button class="ghost-action" disabled>导入图书</button>
            <button class="ghost-action" disabled>管理图书</button>
          </div>
        </div>
        <p class="library-subtitle">你的个人图书库入口已经接入主界面，后续会在这里完成导入、管理、阅读与伴读聊天。</p>
      </div>
    </header>

    <section class="hero-panel">
      <div class="hero-copy">
        <span class="eyebrow">Book Space</span>
        <h1>把书带进唯信，再和“作者”一起读。</h1>
        <p>
          当前版本先交付图书库一级入口、页面骨架和导航恢复策略。你已经可以从左侧导航稳定进入这里，并在刷新后回到最近一次一级入口。
        </p>
      </div>

      <div class="hero-card">
        <div class="hero-card-head">
          <Library :size="18" />
          <span>本 Story 交付范围</span>
        </div>
        <ul class="delivery-list">
          <li v-for="note in deliveryNotes" :key="note">{{ note }}</li>
        </ul>
      </div>
    </section>

    <section class="capability-grid">
      <article v-for="item in capabilities" :key="item.title" class="capability-card">
        <div class="capability-icon">
          <component :is="item.icon" :size="18" />
        </div>
        <div class="capability-title">{{ item.title }}</div>
        <p class="capability-description">{{ item.description }}</p>
      </article>
    </section>

    <section class="workspace-grid">
      <article class="shelf-panel">
        <div class="panel-header">
          <div>
            <div class="panel-title">图书管理主区域</div>
            <p class="panel-subtitle">后续 Story 会在这里接入真实图书数据、封面列表、搜索筛选和作者绑定能力。</p>
          </div>
          <span class="panel-badge">基础布局</span>
        </div>

        <div class="empty-shelf">
          <div class="shelf-illustration" aria-hidden="true">
            <span class="book-spine spine-green"></span>
            <span class="book-spine spine-dark"></span>
            <span class="book-spine spine-light"></span>
            <span class="book-spine spine-soft"></span>
          </div>
          <h2>图书库容器已准备完成</h2>
          <p>当前没有接入真实书籍数据。本页面先承担导航落点和主界面结构职责，后续能力将在此基础上逐步展开。</p>
          <div class="status-row">
            <span v-for="stage in statusStages" :key="stage" class="status-chip">
              {{ stage }}
            </span>
          </div>
        </div>
      </article>

      <aside class="roadmap-panel">
        <div class="panel-title">下一步能力</div>
        <div class="roadmap-list">
          <div class="roadmap-item">
            <div class="roadmap-index">01</div>
            <div class="roadmap-content">
              <div class="roadmap-name">导入与解析</div>
              <p>接入多格式导入、处理状态和失败原因展示。</p>
            </div>
          </div>
          <div class="roadmap-item">
            <div class="roadmap-index">02</div>
            <div class="roadmap-content">
              <div class="roadmap-name">图书管理</div>
              <p>支持封面列表、搜索、删除和绑定作者好友。</p>
            </div>
          </div>
          <div class="roadmap-item">
            <div class="roadmap-index">03</div>
            <div class="roadmap-content">
              <div class="roadmap-name">阅读与伴读</div>
              <p>进入阅读器后，基于当前阅读位置与作者 AI 进行上下文聊天。</p>
            </div>
          </div>
        </div>

        <button class="return-action" @click="emit('back-chat')">
          返回聊天主页
          <ArrowRight :size="16" />
        </button>

        <div class="footnote">
          <BookmarkCheck :size="16" />
          <span>刷新恢复按最近一级入口处理；未来若进入阅读器子视图，也将先回落到“与作者共读”入口。</span>
        </div>
      </aside>
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

.phase-pill {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(7, 193, 96, 0.12);
  color: #03874d;
  font-size: 11px;
  font-weight: 600;
}

.library-subtitle {
  max-width: 820px;
  font-size: 13px;
  line-height: 1.6;
  color: #6b7280;
}

.back-btn,
.ghost-action,
.return-action {
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

.ghost-action {
  min-width: 96px;
  height: 34px;
  padding: 0 14px;
  border: 1px solid rgba(202, 210, 202, 0.9);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.84);
  color: #8b9097;
  font-size: 12px;
  cursor: not-allowed;
}

.hero-panel,
.capability-grid,
.workspace-grid {
  padding-left: 24px;
  padding-right: 24px;
}

.hero-panel {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(280px, 0.86fr);
  gap: 20px;
  padding-top: 24px;
}

.hero-copy,
.hero-card,
.capability-card,
.shelf-panel,
.roadmap-panel {
  border: 1px solid rgba(217, 224, 217, 0.96);
  background: rgba(255, 255, 255, 0.8);
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.05);
  backdrop-filter: blur(16px);
}

.hero-copy {
  padding: 28px;
  border-radius: 28px;
}

.eyebrow {
  display: inline-flex;
  padding: 5px 10px;
  border-radius: 999px;
  background: rgba(7, 193, 96, 0.08);
  color: #0a8b52;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.hero-copy h1 {
  margin-top: 18px;
  color: #1f2937;
  font-size: clamp(26px, 4vw, 38px);
  line-height: 1.16;
  font-weight: 700;
  max-width: 12ch;
}

.hero-copy p {
  margin-top: 16px;
  max-width: 58ch;
  color: #5f6b63;
  font-size: 14px;
  line-height: 1.8;
}

.hero-card {
  padding: 24px;
  border-radius: 24px;
}

.hero-card-head {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #1f2937;
  font-size: 15px;
  font-weight: 600;
}

.delivery-list {
  margin: 18px 0 0;
  padding-left: 18px;
  color: #5f6b63;
  font-size: 13px;
  line-height: 1.8;
}

.capability-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  padding-top: 18px;
}

.capability-card {
  padding: 22px;
  border-radius: 24px;
}

.capability-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 14px;
  background: linear-gradient(135deg, rgba(7, 193, 96, 0.14), rgba(7, 193, 96, 0.05));
  color: #0a8b52;
}

.capability-title {
  margin-top: 18px;
  color: #1f2937;
  font-size: 16px;
  font-weight: 600;
}

.capability-description {
  margin-top: 10px;
  color: #6b7280;
  font-size: 13px;
  line-height: 1.7;
}

.workspace-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(300px, 0.78fr);
  gap: 20px;
  padding-top: 18px;
  padding-bottom: 24px;
}

.shelf-panel,
.roadmap-panel {
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
  max-width: 60ch;
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

.status-row {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 10px;
  margin-top: 22px;
}

.status-chip {
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(215, 221, 215, 0.96);
  color: #5f6b63;
  font-size: 12px;
  font-weight: 600;
}

.roadmap-panel {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 24px;
}

.roadmap-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.roadmap-item {
  display: flex;
  gap: 12px;
  padding: 16px;
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(247, 249, 247, 0.95) 0%, rgba(239, 243, 239, 0.95) 100%);
  border: 1px solid rgba(223, 228, 223, 0.96);
}

.roadmap-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 12px;
  background: rgba(7, 193, 96, 0.12);
  color: #03874d;
  font-size: 13px;
  font-weight: 700;
}

.roadmap-name {
  color: #1f2937;
  font-size: 14px;
  font-weight: 600;
}

.roadmap-content p {
  margin-top: 6px;
  color: #6b7280;
  font-size: 13px;
  line-height: 1.7;
}

.return-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  height: 42px;
  border: none;
  border-radius: 14px;
  background: linear-gradient(135deg, #07c160 0%, #10a04e 100%);
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}

.return-action:hover {
  transform: translateY(-1px);
  box-shadow: 0 12px 24px rgba(7, 193, 96, 0.22);
}

.footnote {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 14px 16px;
  border-radius: 16px;
  background: rgba(248, 250, 248, 0.9);
  color: #5f6b63;
  font-size: 12px;
  line-height: 1.7;
}

@media (max-width: 1080px) {
  .hero-panel,
  .workspace-grid {
    grid-template-columns: 1fr;
  }

  .capability-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 767px) {
  .library-header,
  .hero-panel,
  .capability-grid,
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
  }

  .ghost-action {
    flex: 1;
  }

  .back-btn {
    display: inline-flex;
    align-items: center;
  }

  .hero-copy,
  .hero-card,
  .shelf-panel,
  .roadmap-panel,
  .capability-card {
    border-radius: 22px;
  }

  .hero-copy {
    padding: 24px 18px;
  }

  .hero-copy h1 {
    max-width: none;
    font-size: 28px;
  }

  .empty-shelf {
    min-height: 300px;
    padding: 20px 16px;
  }

  .empty-shelf h2 {
    font-size: 21px;
  }
}
</style>
