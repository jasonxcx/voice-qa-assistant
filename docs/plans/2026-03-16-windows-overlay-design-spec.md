# Windows Overlay Teleprompter - Design Spec (Phase 3)

目标：定义字幕叠加层的视觉与交互设计规范，形成可复用的设计系统令牌，确保跨显示器与不同背景场景下的可读性与美观性。

设计要点
- 字幕区域定位：底部居中，单屏时宽度占比 70%–90%，多显示器时可按主显示器或固定显示器定位。
- 字体与字号：优先使用清晰的显示字体；正文字幕 22–28 px，强调文本 28–34 px。
- 颜色与对比：背景 rgba(0,0,0,0.42)，文本白色；支持高对比度模式。
- 阴影与圆角：文本阴影 0 2px 6px，字幕框圆角 8–14 px，边框尽量轻微。
- 换行与对齐：长文本自动换行，段落对齐左对齐，必要时提供居中对齐选项。
- 动效：平滑滚动/过渡，避免跳动。
- 辅助选项：放大、放大文本、字幕导出、复制文本等扩展能力。

设计系统令牌（Tokens）示例
- colors: --overlay-bg: rgba(0,0,0,0.42); --overlay-text: #ffffff; --overlay-shadow: rgba(0,0,0,0.35);
- typography: --font-display: 'Segoe UI', sans-serif; --font-body: 'Segoe UI', sans-serif; --size-lg: 34px; --size-md: 24px;
- spacing: --pad: 12px; --radius: 12px; --shadow: 0 6px 20px rgba(0,0,0,0.35);
- layout: --overlay-width-perc: 0.85; --overlay-bottom-gap: 40px;

无障碍与可访问性
- 提供高对比度模式、文本放大选项、对屏幕阅读器友好标签。
- 计算文本高度以避免裁切，确保多行文本完整可见。

与现有提词器的对比要点
- 极简 UI、稳定的文本更新接口、无干扰的遮挡策略、易于在多显示器场景下定位。
- 与后端文本源（LLM/本地服务）的对接应提供稳定、低延迟的推送接口。

变更记录
- Phase 3 将基于 Phase 2 的实现，输出具体的 CSS/样式表或 Qt Stylesheet 的 token 化实现。
