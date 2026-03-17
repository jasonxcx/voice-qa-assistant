# Windows Overlay Teleprompter - Research Plan

> I will research Windows 平台上用于屏幕叠加显示的方案，聚焦透明覆盖、始终置顶、鼠标穿透、跨显示器定位，以及多显示器场景的处理，为后续实现阶段提供可落地的技术方案和参考资料。

Goal: 形成可落地的技术评估与实现路线，为后续 Phase 2–5 的具体实现提供可执行的设计与选择。

Architecture: 采用分层评估模型，优先评估 Electron 基于浏览器渲染的透明覆层方案，在多显示器和鼠标穿透方面采用原生 API/Electron APIs 的组合；对比 PyQt 等本地 UI 框架在 Windows 平台的原生能力与维护成本，确保跨语言方案的成本-收益平衡。

Tech Sources & Key Points:
- Electron BrowserWindow 透明覆盖与穿透：transparent、frame: false、alwaysOnTop、setIgnoreMouseEvents 等 API 的组合、以及跨显示器定位能力。
- Windows 原生方案：WS_EX_LAYERED、WS_EX_TRANSPARENT、SetLayeredWindowAttributes、UpdateLayeredWindow，以及多显示器枚举与 DPI 处理。
- PyQt / Qt 方案：WA_TranslucentBackground、Qt::FramelessWindowHint、WindowStaysOnTopHint，以及在 Windows 上的透传鼠标事件处理（WS_EX_TRANSPARENT/Qt 的鼠标穿透组合）。
- 多显示器定位策略：通过系统显示信息获取显示器矩形，计算底部居中位置，支持对目标显示器的切换。
- 性能与无干扰性：overlay 应尽量轻量，避免阻塞视频播放，文本渲染需高对比度、可读性强且支持自适应换行。
- 参考现有提词器应用的 UX/UI 模式：极简、可控、快捷键驱动，支持文本来源灵活性（本地/网络/LLM 输出）与易于集成。

参考资料与要点（示例链接，实际请以最新资料为准）:
- Electron 文档：BrowserWindow 相关选项（transparent, frame, alwaysOnTop, setIgnoreMouseEvents）
- Windows API：WS_EX_LAYERED、WS_EX_TRANSPARENT、SetLayeredWindowAttributes、UpdateLayeredWindow（MSDN / docs）
- Windows DPI 与多显示器 API（DisplaySettings、EnumDisplayMonitors）
- Qt / PyQt 透明窗口和鼠标穿透实现要点（WA_TranslucentBackground、WA_TransparentForMouseEvents）
- 提词器 UX 设计要点与无干扰性设计实践

实现要点与风险:
- 透明覆盖的可访问性与可用性：确保字幕在不同背景下具有清晰对比，提供高对比度模式与放大选项。
- 多显示器场景的定位稳定性：需要对显示器变化事件进行快速响应，确保字幕始终位于目标显示器底部居中。
- 鼠标穿透的正确性：Overlays 必须在不影响用户操作的前提下仅呈现文本，需严格测试鼠标穿透行为，避免卡死/阻塞鼠标。
- DPI 与缩放：不同屏幕的缩放比可能不同，需对字体尺寸/像素进行 DPI 适配。
- 安全性与依赖管理：跨进程通信（IPC/WebSocket）需要有清晰的接口与错误处理。

下一步（Phase 2 目标）:
- 基于 Phase 1 的研究结果，给出两种实现路线的详细对比（Electron 为主、PyQt 作为备用）及权衡。
- 制定最小可运行实现的计划（代码骨架、模块职责、接口设计）。

参考链接（示例，实际请更新为最新资料）:
- Electron Docs: BrowserWindow - https://www.electronjs.org/docs/latest/api/browser-window
- Windows API: WS_EX_LAYERED, WS_EX_TRANSPARENT - https://docs.microsoft.com/windows/win32/api/winuser/nf-winuser-setwindowlongptrw
- Windows Display APIs: EnumDisplayMonitors 等 - https://docs.microsoft.com/windows/win32/api/winuser/nf-winuser-enumdisplaymonitors
- Qt / PyQt Transparency: WA_TranslucentBackground - https://doc.qt.io/qt-6/qtgui/qt.html#WA_TranslucentBackground
- 提词器 UX 最佳实践（摘要）

下一步计划:
- Phase 2 计划：给出技术栈对比与推荐
- Phase 3 计划：字幕样式与设计系统令牌
- Phase 4 计划：最小可运行代码框架
- Phase 5 计划：参考提词器实现要点与风险清单
