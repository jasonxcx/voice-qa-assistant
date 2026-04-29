## 1. 配置项添加

- [x] 1.1 在 `config.yaml.template` 添加 `conversation.enabled: true`
- [x] 1.2 在 `config.yaml.template` 添加 `conversation.max_history_length: 5`
- [x] 1.3 在 `config.yaml.template` 添加 `conversation.truncate_length: 200`
- [x] 1.4 在 `config.yaml.template` 添加 `conversation.followup.enabled: true`
- [x] 1.5 在 `config.yaml.template` 添加 `conversation.followup.max_suggestions: 3`
- [x] 1.6 在 `core/config.py` 添加配置项读取方法（property accessors）

## 2. CaptionHistory 扩展（复用现有模块）

- [x] 2.1 实现 `get_history_for_prompt()` 方法（返回格式化历史，按时间正序）
- [x] 2.2 实现 `_truncate_answer()` 内部方法（限制 200 字）
- [x] 2.3 实现滑动窗口逻辑（超过 N 条移除最旧，N 从配置读取）
- [x] 2.4 处理边界：max_history_length=0 时返回空，流式失败不保存
- [x] 2.5 实现 `clear_history()` 方法（清空所有页面）

## 3. Prompt 注入改造

- [x] 3.1 修改 `LLMClient.build_system_prompt()` 接受 `history_text` 参数
- [x] 3.2 调整注入位置：在文档信息之后、回答规则之前插入历史
- [x] 3.3 格式化历史为：`## 前序对话（供参考）\nQ: ...\nA: ...`
- [x] 3.4 修改 `generate_answer_stream()` 从 `caption_history.get_history_for_prompt()` 获取历史并传递
- [x] 3.5 修改 `generate_answer()` 同上
- [x] 3.6 添加历史为空时不注入的逻辑

## 4. MainWindow 集成

- [x] 4.1 在 `_generate_and_show_answer_stream()` 获取历史：`self.overlay.caption_history.get_history_for_prompt()`
- [x] 4.2 传递历史到 `llm_client.generate_answer_stream()`
- [x] 4.3 新增「开始新会话」按钮 UI
- [x] 4.4 实现「开始新会话」按钮点击处理（调用 `overlay.caption_history.clear_history()`）
- [x] 4.5 添加 `followup_signal = Signal(list)` 用于追问建议传递（通过 PyQt 信号在主线程更新）
- [x] 4.6 连接 `followup_signal` 到 overlay 显示追问的逻辑

## 5. 追问建议功能

- [x] 5.1 在 `LLMClient` 添加 `generate_followup_suggestions()` 方法
- [x] 5.2 设计追问建议 prompt 模板（包含当前 Q&A + 历史上下文）
- [x] 5.3 在回答完成后异步触发追问生成（独立线程）
- [x] 5.4 追问建议通过 `followup_signal.emit()` 发送到 UI（通过 PyQt 信号在主线程更新，不存入历史）
- [x] 5.5 追问建议标注「仅供参考」
- [x] 5.6 处理边界：历史为空时生成通用开场问题，或跳过追问

## 6. UI 展示（可选）

- [x] 6.1 在 `OverlayWindow` 添加追问建议折叠区域
- [x] 6.2 实现追问建议显示/隐藏切换
- [x] 6.3 根据配置 `enable_followup` 控制默认显示状态
- [x] 6.4 追问建议样式设计（与回答区分）

## 7. 测试与验证

- [x] 7.1 手动测试历史注入效果（连续 3 轮问答）
- [x] 7.2 验证滑动窗口正确移除最旧记录
- [x] 7.3 验证「开始新会话」清空功能
- [x] 7.4 验证追问建议生成正确性
- [x] 7.5 测试 `max_history_length: 0` 时无历史注入且无追问
- [x] 7.6 测试 `enable_followup: false` 时无追问生成
- [x] 7.7 测试历史为空时追问建议生成（通用开场问题）
- [x] 7.8 测试流式回答中途失败，历史不保存部分回答