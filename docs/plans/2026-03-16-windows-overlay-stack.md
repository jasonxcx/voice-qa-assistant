# Windows Overlay Teleprompter - Technology Stack & Evaluation

Phase 2 Objective
- 给出两套实现路线的技术栈对比，并给出在 Windows 场景中的可行性、开发效率和维护性。

## 2. Phase 2: 技术栈对比与推荐 (Electron 为主，PyQt/Tkinter 备选)

### 2.1 综合结论（推荐路线）
- 首选方案：Electron 方案作为主栈，因其在 Windows 上对透明覆盖、跨显示器定位、以及与前端/UI 的协作能力最成熟，且易于与本地/云端大模型输出建立实时文本推送接口。
- 备选方案：PyQt/PySide 作为本地原生实现选项，便于小体积部署、对 Python 生态的深度集成，以及拥有稳定的桌面应用体验；但在跨平台一致性和 UI/UX 上的灵活性略逊于 Electron。

### 2.2 方案对比（关键维度）
- 实现难度：Electron 高度熟悉前端的开发者，PyQt 需要 Qt 的熟悉度。
- 开发效率：Electron 通过 Web 技术快速迭代，UI/UX 调整更便捷；PyQt 需要较多 Qt 样式表与信号槽编程。 
- 部署/打包：Electron 的打包工具链成熟，Windows 打包简单；PyQt 的 PyInstaller/cx_Freeze 也成熟，但对依赖的打包要细腻处理。 
- 性能与资源占用：PyQt 通常内存较低，Electron 需留意内存占用，但对复杂 UI 的渲染能力强。
- 与后端/LLM 的对接：Electron 通过 Node.js 易于实现本地 HTTP/WebSocket 客户端；PyQt 需要额外的进程/服务搭建来实现同样的对接。 
- 维护成本：Electron 的前端生态和广泛的社区资源有利于长期维护；PyQt 在纯桌面环境下维护简单但跨平台性略弱。

### 2.3 Windows 场景要点
- Electron：透明叠加窗口、无边框、始终置顶、鼠标穿透在 Windows 下支持良好，跨显示器定位性能稳定；对 DPI 缩放要进行额外处理。
- PyQt：Windows 下可通过 WA_TranslucentBackground、WS_EX_TRANSPARENT 的组合实现鼠标穿透，但跨显示器定位和 DPI 处理需要额外工作。

### 2.4 维护性与前瞻性
- 如果团队具备 Web/前端能力，Electron 的长期维护和扩展性将更好。
- 如未来需要将落地部署为极小体积的原生应用，PyQt 提供更轻量的选项，但将牺牲部分跨平台一致性与快速迭代能力。

### 2.5 下一步（Phase 4 的骨架）
- 基于上文对比，选择 Electron 为主实现路线，编写最小可运行的实现骨架（Phase 4 的文件与接口设计）。若需要，附带 PyQt 的替代实现要点。 

说明：Phase 2 的输出将直接作为 Phase 3/Phase 4 的输入，确保设计的一致性和实现的可落地性。
- 给出两套实现路线的技术栈对比，并给出在 Windows 场景中的可行性、开发效率与维护性评估。

方案 A（首选）：Electron 作为主栈
- 结构概览：Electron 主进程负责窗口创建与系统级 API 交互，渲染进程负责字幕文本的美化呈现，借助 IPC/WebSocket 与后端大模型服务对接字幕内容。
- 关键点：透明覆盖、无边框、AlwaysOnTop、鼠标穿透、跨显示器定位、DPI 适配、性能优化（尽量轻量的渲染）
- 优点：跨平台、快速原型、丰富的前端样式能力、便于与现有 Web 技术栈集成、与 Python/LLM 服务对接简单。
- 缺点：需要打包 Electron 应用，体积较大、对本地机器性能要求略高、对桌面集成细致程度需自行实现（如 DPI、触摸/手势支持）

方案 B：PyQt/PySide（Qt 框架，作为次选）
- 结构概览：PyQt 实现一个本地原生应用，透明覆盖窗口，鼠标穿透通过 WS_EX_TRANSPARENT（Win API）或 Qt 的鼠标穿透能力实现。
- 关键点：WA_TranslucentBackground、Frameless、WindowStaysOnTop、跨显示器定位、DPI 适配。
- 优点：对 Python 生态友好、对接本地 LLM 服务与后端 Python 容易，应用体积通常比 Electron 小，性能/响应可能更好。
- 缺点：跨平台支持略差（若后续要扩展到其他平台需额外工作），UI 样式定制相对繁琐，需要对 Qt 栈有较深理解。

对比要点（简表）
- 开发效率：Electron 高（前端/网页熟悉度高） vs PyQt 中等（需熟悉 Qt 信号/槽、样式表）
- 体积与依赖：Electron 较大，PyQt 相对小
- 框架生态：Electron 拥有大规模社区与生态，Qt 提供稳定的桌面应用能力
- 跨平台能力：两者均可扩展，Electron 跨平台更自然，Qt 需要额外的打包工作以保证原生体验

推荐结论
- 首选方案：Electron 方案，若现有后端已经使用 Python/LLM 服务，Electron + Python 服务的组合最具灵活性。
- 备选：PyQt 作为单机高性能原生实现时的替代选项，便于微调 UI/UX 与底层性能。

落地要点
- 统一的对外接口设计：字幕文本更新通过 IPC/WebSocket，便于后端替换、测试与回退。
- 趋向最小可行性实现：先实现单显示器、底部居中、不遮挡的视频视野的 Overlay；再扩展到多显示器、滚动文本等。
- 版本与打包策略：Electron 方案使用现有打包工具链（如 electron-builder），PyQt 方案采用 PyInstaller/cx_Freeze 等。

下一步建议的工作流
- Phase 3 进入：定义字幕样式与设计令牌（字体、颜色、透明度、阴影、圆角等）。
- Phase 4 进入：基于选定栈搭建最小可运行框架的代码骨架。 

附注：如需，我可在下一步将 Phase 4 的骨架代码按选定栈展开为具体文件清单与实现步骤。
