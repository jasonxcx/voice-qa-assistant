# Tasks — redesign-main-window-ui

## 1. PySide6 迁移 (前置依赖)

- [x] 1.1 更新 `requirements.txt`：替换 `PyQt5` 为 `PySide6`
- [x] 1.2 批量替换 `app.py` 中的 `from PyQt5.QtWidgets import QApplication` → `from PySide6.QtWidgets import QApplication`
- [x] 1.3 批量替换 `ui/main_window.py` 中所有 `PyQt5` import → `PySide6` (QtCore, QtWidgets, QtGui)
- [x] 1.4 批量替换 `ui/overlay_window.py` 中所有 `PyQt5` import → `PySide6`
- [x] 1.5 批量替换 `ui/styles.py` 中所有 `PyQt5` import → `PySide6` (如有)
- [x] 1.6 替换所有 `pyqtSignal` → `Signal` (from PySide6.QtCore)
- [x] 1.7 替换所有 `pyqtSlot` → `Slot` (如有使用)
- [x] 1.8 运行 `python app.py` 验证 PySide6 迁移成功，确保无 ImportError
- [ ] 1.9 测试所有信号/槽连接正常工作 (start_btn, overlay hotkeys, audio signals)

## 2. Phase 1 — 样式基础设施

- [x] 2.1 在 `ui/styles.py` 定义新颜色常量：BACKGROUND, SURFACE, SURFACE_HOVER, BORDER, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, ACCENT_PRIMARY, ACCENT_HOVER, ACCENT_ACTIVE, SUCCESS, WARNING, ERROR
- [x] 2.2 在 `ui/styles.py` 定义按钮样式类：PRIMARY_BUTTON, SECONDARY_BUTTON, DANGER_BUTTON, ICON_BUTTON (QSS string)
- [x] 2.3 在 `ui/styles.py` 定义卡片样式类：CARD_CONTAINER, CARD_HEADER (QSS string)
- [x] 2.4 在 `ui/styles.py` 添加 Overlay 专用常量：OVERLAY_BG_SOLID, OVERLAY_SHADOW, OVERLAY_LISTEN_ACTIVE, OVERLAY_LISTEN_INACTIVE
- [ ] 2.5 更新 `ui/overlay_window.py`：将所有 inline RGBA 颜色替换为引用 `styles.py` 常量
- [ ] 2.6 测试 OverlayWindow 新样式渲染正常，透明度、阴影、按钮颜色均正确
- [ ] 2.7 更新 `ui/main_window.py`：创建全局样式字符串引用新的常量系统 (暂不应用，仅准备)

## 3. Phase 2 — MainWindow 布局重构

- [ ] 3.1 创建 `ui/main_window_tabs.py` 新文件：定义 QTabWidget 结构骨架 (4 tabs)
- [ ] 3.2 在 MainWindow 中添加 feature flag `_use_new_layout = True/False`，允许新旧布局切换
- [ ] 3.3 实现 **主面板 (Main)** tab 内容：状态显示、文档路径、开始/停止按钮、字幕窗口开关
- [ ] 3.4 实现 **LLM 设置** tab 内容：Provider 选择、Model 输入、Base URL、API Key (Basic tier)
- [ ] 3.5 实现 **LLM 设置** tab Advanced 折叠区：`llm.generation.temperature`, `llm.generation.max_completion_tokens`, `llm.generation.reasoning_effort`, prompts 配置
- [ ] 3.6 实现 **STT 设置** tab 内容：Model 选择、Device 选择、Compute type (Basic tier)
- [ ] 3.7 实现 **STT 设置** tab Advanced 折叠区：`stt.auto.*` 7 个阈值、`stt.download.mirror`, `stt.download.cache_dir`, `stt.language`, `stt.hotwords`
- [ ] 3.8 实现 **显示设置** tab 内容：Overlay 高度/宽度比例、字体大小、热键配置
- [ ] 3.9 迁移所有现有 UI 逻辑到新 tab widgets (设备刷新、model 加载、config sync)
- [ ] 3.10 测试新旧 layout 切换正常，feature flag = False 时旧 layout 可用
- [ ] 3.11 测试 feature flag = True 时新 layout 正常，所有 tabs 可切换

## 4. Phase 3 — 配置 UI 暴露

- [ ] 4.1 更新 `config.yaml.template`：添加 `document.path: ""`、`audio.use_microphone`、`audio.input_device_index`、`audio.output_device_index`
- [ ] 4.2 更新 `core/config.py`：添加 `document_path` property accessor
- [ ] 4.3 实现 `_update_config_from_ui()` 遍历所有新 UI 控件并同步到 config
- [ ] 4.4 实现每个 UI 控件的 config 绑定：QComboBox → config.set(), QLineEdit → config.set(), QSlider → config.set()
- [ ] 4.5 实现音频设备变更立即生效：调用 `restart_monitoring()` (已有，确保新 UI 正确触发)
- [ ] 4.6 实现模型变更提示：STT model/device/compute_type 变更时显示 "需重启监听生效" tooltip
- [ ] 4.7 实现保存按钮逻辑：`config.save()` + `llm_client.switch_mode()` (已有，确保新 UI 正确触发)
- [ ] 4.8 实现配置 auto-save + debounce：使用 QTimer.singleShot(500, save) 对 slider 等高频变更
- [ ] 4.9 实现每个配置项的 tooltip：描述用途、有效范围、副作用
- [ ] 4.10 实现 "Reset to defaults" 按钮：读取 config.yaml.template 恢复当前 section 默认值

## 5. Phase 3 — 文档路径持久化

- [ ] 5.1 添加 `DocumentPathWidget`：QLineEdit + QPushButton(Browse) + QToolButton(Status Icon)
- [ ] 5.2 实现 Browse 按钮：打开 QFileDialog，过滤 .md/.markdown，起始目录为当前 path
- [ ] 5.3 实现路径选择后逻辑：验证文件存在 → `parse_resume()` → 存入 `config.document.path` → `config.save()`
- [ ] 5.4 实现 status indicator：文件存在显示绿色 checkmark，不存在显示红色 warning icon
- [ ] 5.5 实现 MainWindow 启动时路径恢复：读取 `config.document.path` → 验证 → 自动加载 → 更新 UI
- [ ] 5.6 实现 "Clear document" 按钮：清空 `config.document.path` → 清空 `resume_data` → 重置 UI 为 "No document"
- [ ] 5.7 实现路径字段可手动编辑：Enter 键触发验证和加载
- [ ] 5.8 测试完整流程：选择文档 → 重启 app → 自动加载 → 清空 → 重启 → 空状态

## 6. Phase 4 — 完善与验证

- [ ] 6.1 实现窗口 geometry 持久化：`saveGeometry()` → Base64 → 存入 `config.ui.window_geometry`
- [ ] 6.2 实现启动时 geometry 恢复：读取 config → `restoreGeometry()` (如非 null)
- [ ] 6.3 实现表单验证反馈：API Key 为空时显示红色边框，URL 格式错误显示 tooltip
- [ ] 6.4 实现模型加载进度指示：替换 button spinner 为 QProgressBar 或 loading overlay
- [ ] 6.5 实现 Loading Overlay：QWidget overlay 遮罩主窗口，禁用所有控件，显示 "加载中..."
- [ ] 6.6 实现 Volume slider：将静态 volume label 替换为实时 QSlider 可视化
- [ ] 6.7 最终集成测试：运行 `python app.py` 确认所有功能正常
- [ ] 6.8 测试所有热键功能：Ctrl+F4/F6/F7/F8/F9 在新 overlay 下正常工作
- [ ] 6.9 测试 config 读写：修改任意配置 → 重启 → 配置正确恢复
- [ ] 6.10 清理：移除 feature flag，删除旧 groupbox layout 代码，移除 PyQt5 遗留