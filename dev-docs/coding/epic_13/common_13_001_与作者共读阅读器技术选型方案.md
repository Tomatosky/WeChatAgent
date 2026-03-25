# 与作者共读阅读器技术选型方案

> **文档目标**: 为 Epic 13「与作者共读」提供一份偏工程落地的阅读器技术选型结论，优先遵循“尽量不重复造轮子、优先开箱即用、兼容现有技术栈”的原则。

## 1. 背景与目标

### 1.1 当前项目技术栈
- 前端：Vue 3 + TypeScript + Vite
- 桌面端：Electron
- 后端：FastAPI + Python
- 当前 UI 架构：单页应用主视图切换，不是现成的多页面阅读器产品

### 1.2 本次选型目标
- 尽量复用成熟开源库，避免从零实现 EPUB/PDF 排版与渲染
- 尽量支持 Epic 13 期望的格式：`EPUB / PDF / MOBI / AZW / AZW3 / TXT`
- 支持后续能力扩展：
  - 阅读器打开与浏览
  - 目录导航
  - 阅读进度恢复
  - 选中文字引用
  - 右侧伴读聊天上下文注入
- 尽量降低前端维护成本和协议兼容风险

### 1.3 关键现实约束
- 市面上**没有一个在 Web/Electron 场景下成熟稳定、真正“拿来就能吃下所有目标格式”的通用阅读器组件库**。
- “支持导入”与“支持高质量阅读/选中/引用/目录/定位”是两回事。
- `MOBI / AZW / AZW3` 在 Web 端支持普遍弱于 `EPUB / PDF`，且 DRM 是刚性边界。

## 2. 候选方案调研结论

### 2.1 方案 A：直接集成完整开源阅读器应用

候选代表：
- Koodo Reader
- KOReader

#### 优点
- 功能丰富，格式支持广，具备成熟阅读器产品能力
- 可作为交互和实现参考

#### 缺点
- 这类项目通常是**完整应用**，不是为 Vue 组件嵌入设计的 SDK
- 代码体量大，二次裁剪与嵌入成本高
- 与 DouDouChat 当前前端架构集成复杂
- 许可风险较高

#### 结论
- **不推荐作为直接集成方案**
- **推荐作为参考实现和交互对标对象**

#### 备注
- `Koodo Reader` 官方 README 显示支持 `EPUB / PDF / DRM-free MOBI / AZW3 / AZW / TXT` 等多格式，但其许可证为 **AGPL-3.0**，官方文档还明确说明，如果使用其代码，项目需要按同许可证开源，并注明基于 Koodo Reader。
- 对当前项目来说，这不适合作为“直接嵌入核心代码”的路线。

### 2.2 方案 B：单一 Web 阅读引擎覆盖大部分格式

候选代表：
- `foliate-js`

#### 优点
- 纯 JavaScript，天然适合浏览器与 Electron
- 官方说明支持 `EPUB / MOBI / KF8(AZW3) / FB2 / CBZ / PDF(实验性)`
- 自带 demo reader，可作为快速原型基础
- MIT 许可证，许可友好
- 比“`epub.js + 一堆自拼解析器`”更接近一体化方案

#### 缺点
- 官方明确说明 **API 目前不稳定**
- 自带 `reader.html` 只是 demo，且功能并不完整，不应当视为现成生产级组件
- PDF 仍是实验性支持
- 仍需要我们自己封装 Vue 组件、阅读器状态、工具栏和项目内数据流

#### 结论
- **推荐作为多格式阅读核心引擎的首选候选**
- 但必须接受它是“半成品内核 + 自己封装壳层”的路线，不是 npm 一装就结束

### 2.3 方案 C：按格式拆分成熟库，各自处理

候选代表：
- EPUB：`epub.js`
- PDF：`PDF.js` 或 `vue-pdf-embed`
- TXT：自实现轻量阅读器
- MOBI / AZW3：另行处理

#### 优点
- `EPUB` 和 `PDF` 路线最成熟
- 社区规模大，问题资料多
- 对 Vue 3 友好，尤其 `vue-pdf-embed` 开箱度高
- 可精确控制不同格式的能力边界

#### 缺点
- 方案割裂，前端要维护多套阅读器接入逻辑
- `MOBI / AZW / AZW3` 仍然缺一套同等级成熟方案
- UI 与数据模型统一成本更高

#### 结论
- **推荐作为最稳妥的兜底方案**
- 若 `foliate-js` 原型效果不达标，应切换为这条路线

### 2.4 方案 D：Readium 体系

候选代表：
- `readium/web`

#### 优点
- 阅读标准化程度高
- 长期看适合做专业 Web Reader
- BSD-3-Clause，许可友好

#### 缺点
- 官方当前明确写明：**目前支持 EPUB，PDF 仍在计划中**
- 更适合“围绕 EPUB 构建专业阅读器”，不适合当前多格式快速落地目标

#### 结论
- **当前阶段不作为首选**
- 如果未来产品方向收敛到 EPUB 专业阅读器，可重新评估

## 3. 最终推荐方案

## 3.1 总体结论

**推荐采用“混合方案”，而不是强行追求一个单库全包。**

推荐顺序如下：

1. **主推荐路线**
   - 以 `foliate-js` 作为多格式阅读核心候选
   - 对 PDF 保留 `PDF.js` / `vue-pdf-embed` 兜底
   - TXT 使用最小自定义阅读适配
2. **保守兜底路线**
   - EPUB 使用 `epub.js`
   - PDF 使用 `PDF.js` / `vue-pdf-embed`
   - TXT 自实现
   - MOBI / AZW / AZW3 仅做“可导入 + 尝试解析 + 失败明确提示”，或后端预处理转换

核心判断：
- 想要“尽量少造轮子”，`foliate-js` 是最接近目标的开源内核。
- 想要“第一版稳定”，不能只押 `foliate-js`，必须保留 PDF 与异常格式的独立兜底。

## 3.2 不推荐的路线

- 不推荐直接把 `Koodo Reader` 的代码整体搬入当前项目
  - 原因：AGPL 许可约束重、代码体量大、不是组件库、改造成本高
- 不推荐直接承诺第一版完整支持 DRM `AZW/AZW3`
  - 原因：技术与版权边界都不稳定
- 不推荐完全自研阅读器排版引擎
  - 原因：成本高，回报差，且没有必要

## 4. 推荐架构方案

### 4.1 前端总体结构

建议新增一个独立阅读模块，放在前端内部而不是直接塞进 `ChatArea.vue`：

- `front/src/modules/reader/`
  - `ReaderShell.vue`
  - `ReaderToolbar.vue`
  - `ReaderViewport.vue`
  - `ReaderSidebarToc.vue`
  - `ReaderChatPanel.vue`
  - `engines/`
    - `foliateEngine.ts`
    - `epubEngine.ts`
    - `pdfEngine.ts`
    - `txtEngine.ts`
  - `types.ts`
  - `selection.ts`
  - `progress.ts`

核心思想：
- UI 壳层统一
- 具体格式由阅读引擎适配层负责
- 聊天、目录、进度、选区能力统一向上暴露

### 4.2 阅读引擎抽象接口

建议抽象统一接口：

```ts
export interface ReaderEngine {
  load(input: ReaderSource): Promise<void>
  destroy(): Promise<void>
  getCapabilities(): ReaderCapabilities
  getToc(): Promise<ReaderTocItem[]>
  getCurrentLocator(): ReaderLocator | null
  restoreLocator(locator: ReaderLocator): Promise<void>
  getVisibleText(): Promise<string | null>
  getSelectionQuote(): Promise<ReaderQuote | null>
  on(event: ReaderEvent, handler: (...args: any[]) => void): void
}
```

这样上层不直接依赖 `foliate-js` 或 `epub.js` 的具体 API，便于后续替换。

### 4.3 后端职责

后端不负责自己渲染阅读器，但应负责：

- 文件上传与持久化
- 图书元数据存储
- 解析状态记录
- 进度持久化
- 书籍与好友绑定关系
- 伴读会话与普通单聊隔离
- 必要时执行预处理或格式转换

建议后端为每本书记录：

- `format`
- `parse_status`
- `capabilities`
  - `can_read`
  - `can_toc`
  - `can_select_text`
  - `can_chat_context`
  - `can_quote`
- `parse_error`
- `cover_url`

## 5. 各格式落地策略

### 5.1 EPUB

#### 推荐
- 首选：`foliate-js`
- 备选：`epub.js`

#### 理由
- EPUB 是 Web 场景最成熟的电子书格式
- 目录、章节、定位、正文提取都比较友好
- 是最适合做“与作者共读”的主战场格式

#### 第一版目标
- 打开阅读
- 目录导航
- 进度恢复
- 可见文本提取
- 选区引用
- 伴读聊天上下文注入

### 5.2 PDF

#### 推荐
- 首选：`PDF.js`
- Vue 封装优先：`vue-pdf-embed`

#### 理由
- PDF 在渲染稳定性和资料丰富度上最成熟
- `vue-pdf-embed` 对 Vue 3 开箱度高，支持 text layer、annotation layer、密码文档处理

#### 第一版能力边界
- 支持打开与浏览
- 支持目录跳转（若 PDF 自带 outline）
- 支持进度记录
- 仅对**有文本层**的 PDF 启用选区引用和上下文聊天
- 对扫描版 PDF：
  - 可阅读
  - 不承诺引用与精准正文提取

### 5.3 TXT

#### 推荐
- 自实现轻量阅读适配器

#### 理由
- TXT 格式简单，自研成本很低
- 目录通常不存在，不值得引入重型库

#### 第一版能力边界
- 支持打开阅读
- 支持进度恢复
- 支持文本选中
- 可选：按规则切章节
- 对无结构 TXT：不承诺 TOC

### 5.4 MOBI / AZW / AZW3

#### 推荐
- 首选：使用 `foliate-js` 直接尝试支持
- 兜底：失败时进入 `limited` / `failed`
- 可选中期增强：后端预处理转 `EPUB` 或中间格式

#### 理由
- Web 端直接成熟支持较弱
- `foliate-js` 是当前少数明确支持 `MOBI / KF8(AZW3)` 的前端阅读库
- 但性能、兼容性、DRM 边界不能当成“稳定全支持”

#### 第一版能力边界
- 仅承诺支持**无 DRM、可解析**文件
- 若可解析：
  - 支持基础阅读
  - 尽量支持目录、进度、可见文本提取
- 若不可解析：
  - 保留导入记录
  - 明确提示“当前文件受限或暂不支持阅读增强能力”

## 6. 开发阶段建议

### 阶段 1：最小可用版本

目标：
- 尽快交付阅读器主流程

范围建议：
- EPUB：完整支持
- PDF：完整基础阅读 + 有文本层时支持引用/聊天
- TXT：基础支持
- MOBI/AZW/AZW3：仅在 `foliate-js` 验证通过后开放，否则先标 `limited`

### 阶段 2：增强版本

目标：
- 扩展 Kindle 系兼容性

范围建议：
- 增强 `foliate-js` 适配与异常处理
- 研究后端格式预处理方案
- 引入更多定位与文本提取优化

### 阶段 3：体验优化

目标：
- 提升阅读器产品感

范围建议：
- 阅读主题
- 字体字号
- 双栏/滚动模式
- 书签、高亮、批注
- 更强的引用块交互

## 7. 风险评估

### 7.1 主要风险

1. `foliate-js` API 不稳定
2. `MOBI / AZW3` 兼容性不可完全预测
3. PDF 文本提取能力强依赖源文件质量
4. Electron 内嵌阅读器需要注意资源加载与 CSP
5. 多格式统一抽象若设计过死，后续替换引擎成本会上升

### 7.2 风险控制措施

1. 所有具体库都通过 `ReaderEngine` 适配层接入，不直接散落到页面组件
2. 先用真实样本库做 PoC，再决定是否开放特定格式
3. 明确 `ready / limited / failed` 状态，不虚假承诺能力
4. PDF 独立保留 `PDF.js` 兜底
5. 不把 `Koodo Reader` 源码直接并入主工程

## 8. 最终决策建议

### 8.1 决策结论

**推荐选型**：
- 多格式核心：`foliate-js`
- PDF 兜底：`vue-pdf-embed` 或直接 `PDF.js`
- EPUB 兜底：`epub.js`
- TXT：轻量自实现

### 8.2 决策理由

- 最符合“尽量不重复造轮子”的原则
- 保留了多格式能力扩展空间
- 避免直接引入 AGPL 完整应用代码
- 与现有 `Vue 3 + Electron` 技术栈兼容性最好
- 第一版能把主要精力放在“阅读-聊天融合”而不是底层排版重写

### 8.3 明确不承诺事项

第一版不应承诺以下内容：
- DRM 受保护 Kindle 文件可用
- 所有 PDF 都支持精确选区引用
- 所有格式都有 TOC 和页码
- 所有格式都能稳定支持“当前页上下文自动提取”

## 9. 建议的下一步工作

1. 建一个小型 PoC 页面，分别验证：
   - `foliate-js` 读 EPUB
   - `foliate-js` 读 MOBI/AZW3
   - `vue-pdf-embed` 读 PDF 并拿到 text layer
2. 准备一组测试样本：
   - 标准 EPUB
   - 大型 EPUB
   - 文本层 PDF
   - 扫描版 PDF
   - DRM-free MOBI
   - DRM-free AZW3
   - 异常 TXT
3. 根据 PoC 结果再决定：
   - MOBI/AZW3 是否第一版开放
   - PDF 是否走 `vue-pdf-embed` 还是直接 `PDF.js`
4. PoC 通过后，再进入阅读器模块实现文档设计

## 10. 参考资料

- `foliate-js`
  - GitHub: https://github.com/johnfactotum/foliate-js
  - Demo / 文档: https://johnfactotum.github.io/foliate-js/
- `epub.js`
  - GitHub: https://github.com/futurepress/epub.js
- `PDF.js`
  - GitHub: https://github.com/mozilla/pdf.js
- `vue-pdf-embed`
  - GitHub: https://github.com/hrynko/vue-pdf-embed
- `Readium Web`
  - GitHub: https://github.com/readium/web
- `Koodo Reader`
  - GitHub: https://github.com/koodo-reader/koodo-reader
  - License 说明: https://www.koodoreader.com/en/document
