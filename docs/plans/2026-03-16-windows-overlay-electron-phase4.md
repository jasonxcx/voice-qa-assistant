# Windows Overlay Teleprompter - Phase 4: Electron Skeleton Implementation

目标：给出一个最小可运行的 Electron 框架骨架，涵盖主进程、渲染进程、跨显示器定位、鼠标穿透、字幕更新接口，以及一个简单的字幕渲染 UI，并给出 PyQt 的备用实现要点。

文件结构（示例）
- electron-overlay/
  - package.json
  - src/
    - main.js                 // 主进程：窗口创建、定位、穿透、IPC/WebSocket
    - preload.js              // 预加载脚本（可选，增强隔离性）
    - renderer.js             // 渲染进程：字幕渲染与状态管理
  - overlay.html              // 渲染 UI 框架
  - overlay.css               // 样式：字体、颜色、透明度、阴影、圆角等 Tokens
  - tests/
  - package-lock.json

核心实现要素
- 透明覆盖窗口：frameless、transparent，AlwaysOnTop，skipTaskbar。
- 鼠标穿透：overlayWindow.setIgnoreMouseEvents(true, { forward: true })
- 多显示器定位：使用 Electron 的 screen API，定位到目标显示器底部居中。
- 字幕更新接口：IPC 与（可选）WebSocket 实现，接收文本并渲染。
- 简易后端对接：示例使用 ws（WebSocket）或本地 HTTP 服务推送字幕文本。

Phase 4 任务清单
- Task 4.1 初始化 Electron 项目结构与打包脚本。
- Task 4.2 主进程实现：窗口属性、跨显示器定位、鼠标穿透、IPC 通道。
- Task 4.3 渲染进程实现：字幕文本渲染、更新逻辑。
- Task 4.4 对外接口：实现 update-caption(text) 与 set-monitor(displayId) 等 API。
- Task 4.5 可选：WebSocket 服务实现，字幕文本通过 ws 推送。
- Task 4.6 PyQt 备选实现要点：透明窗口、鼠标穿透、底部居中定位的实现要点。
- Task 4.7 基本手动测试用例与运行步骤。

最小代码骨架要点（参考实现要点）
- main.js：创建 BrowserWindow，参数设置、定位、穿透、IPC
- renderer.js：接收字幕文本并更新 UI
- overlay.html/overlay.css：字幕样式模板，使用设计令牌中的变量
- PyQt 备选要点：示例脚本与 Win32 透传实现建议

运行步骤（Electron）
- npm install
- npm start

测试要点
- Overlay 在主显示器底部居中，文本更新实时且换行正常。
- Overlay 为透明背景、文字可读、鼠标穿透且不影响视频区域。
- 多显示器场景下能切换显示器并重新定位。
