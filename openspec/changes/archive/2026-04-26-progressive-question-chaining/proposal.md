## Why

当前面试助手系统独立处理每个问题，缺乏上下文关联。真实面试场景中，面试官会基于候选人回答进行追问（深度挖掘），问题之间存在逻辑递进关系。需要在 LLM 生成回答时考虑前序问答历史，实现渐进式提问体验。

## What Changes

- 新增问答历史管理模块，存储会话中的 Q&A 序列
- 修改 LLM prompt 构建，注入历史上下文
- 新增追问建议功能（可选展示）
- 新增会话管理（开始新会话、查看历史）

## Capabilities

### New Capabilities

- `conversation-history`: 问答历史存储与检索，支持配置最大历史条数、自动清理策略
- `context-injection`: LLM prompt 上下文注入，将历史问答注入系统提示词，支持滑动窗口策略
- `followup-suggestions`: 追问建议生成，基于当前回答生成可能的追问方向

### Modified Capabilities

无现有 spec，无需修改现有能力。

## Impact

**核心模块**:
- `core/llm_client.py`: `build_system_prompt()` 需接收历史上下文参数
- `ui/main_window.py`: 新增会话控制 UI（开始新会话按钮）
- `ui/overlay_window.py`: 可选展示追问建议

**配置项**:
- `conversation.max_history_length`: 最大历史条数（默认 5）
- `conversation.enable_followup`: 是否启用追问建议（默认 true）

**数据存储**:
- 内存存储（当前会话），可选持久化到本地文件