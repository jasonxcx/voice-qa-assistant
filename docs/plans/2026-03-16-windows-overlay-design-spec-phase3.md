# Windows Overlay Teleprompter - Phase 3 Design Spec

目标：将 Phase 2 的 UI/UX 方向细化为可复用的设计规范与令牌，确保 Electron/Qt 实现可以一致地应用风格。

设计要点（摘要）
- 视觉定位：底部居中，单屏宽度 70%–90%，多屏可在主显示器或配置显示器底部居中。
- 字体与字号：正文 22–28px，标题/强调 28–34px，行距 1.25–1.4，换行自适应。
- 背景与对比：背景半透明黑色（如 rgba(0,0,0,0.42)），文本白色，必要时高对比度模式。
- 阴影与圆角：文本阴影 0 2px 6px，字幕框圆角 8–14px，边缘柔和。
- 动效：文本滚动/换行过渡采用平滑过渡，避免抖动。
- 无障碍：高对比度、文本放大、屏幕阅读器友好标签。

设计系统令牌（Tokens）示例
- Colors: --overlay-bg, --overlay-text, --overlay-text-soft, --overlay-shadow
- Typography: --font-display, --font-body, --size-caption, --size-subtitle, --size-title
- Layout: --overlay-width-perc, --overlay-height, --overlay-radius, --overlay-padding
- Effects: --shadow, --blur

示例 JSON（导出 tokens.json）
{
  "colors": {
    "overlayBg": "rgba(0,0,0,0.42)",
    "overlayText": "#ffffff",
    "overlayTextSoft": "rgba(255,255,255,0.92)",
    "overlayShadow": "rgba(0,0,0,0.35)"
  },
  "typography": {
    "fontDisplay": "Segoe UI, PingFang SC, sans-serif",
    "fontBody": "Segoe UI, PingFang SC, sans-serif",
    "sizeCaption": 22,
    "sizeSubtitle": 28,
    "sizeTitle": 34
  },
  "layout": {
    "overlayWidthPerc": 0.85,
    "overlayHeight": 140,
    "overlayRadius": 12,
    "overlayPadding": 12
  },
  "effects": {
    "shadow": "0 6px 20px rgba(0,0,0,0.35)",
    "blur": 2
  }
}

实现要点
- Electron：通过 overlay.css 变量驱动上述令牌，确保渲染的一致性。
- Qt：通过 Stylesheet 参数实现同样的风格，必要时结合自定义控件。
- 提供可编辑的 tokens.json，方便后续在设计端与实现端的对齐。

交付物
- tokens.json、overlay.css 的变量模板、以及一个设计端到实现端的映射说明文档。
