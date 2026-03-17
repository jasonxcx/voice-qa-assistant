# Windows Overlay Teleprompter - Electron Skeleton (Phase 4)

目标：给出一个最小可运行的 Electron 框架骨架，包含主进程、渲染进程、跨显示器定位、鼠标穿透、字幕更新 IPC/WebSocket 接口等核心模块的职责分配与文件结构。

项目结构示例
- electron-overlay/
  - package.json
  - main.js                 // 主进程：创建覆盖窗口、跨显示器定位、穿透设置、IPC 异步接口
  - preload.js              // 预加载脚本（可选，增强隔离性）
  - overlay.html              // 渲染进程 UI 容器
  - overlay.css               // 样式：字体、颜色、透明度、阴影、圆角等 token
  - renderer.js               // 渲染进程：字幕文本渲染与本地状态管理
  - subtitleService.js        // 与外部大模型文本源对接的简单桥接（示例）
  - assets/
  - src/
    - config/
    - services/
  - test/
    - unit/
    - integration/

核心接口设计
- update-caption(text: string): 将新字幕文本推送给 Overlay 渲染层。
- set-position(displayId?: number): 动态切换目标显示器。若无参数，保持当前定位。
- 通过 WebSocket/IPC 封装一个简单的文本流接口，后端可无缝推送字幕。

数据流
- Backend/LLM → subtitleService.js → IPC → renderer.js → overlay.html 渲染文本。
- Overlay 调整文本样式、滚动/换行策略、以及背景透明度等样式属性。

测试要点
- 窗口应为透明底色、字幕文本可读、背景 semi-transparent、文本换行正常。
- Overlay 应在主显示器底部居中，且在显示器改变时能重新定位。
- 鼠标穿透：Overlay 不捕获鼠标事件。
