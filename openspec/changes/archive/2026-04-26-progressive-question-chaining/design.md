## Context

当前系统架构：
- `core/llm_client.py`: LLM 调用入口，`build_system_prompt()` 构建提示词，`generate_answer_stream()` 流式生成
- `ui/overlay_window.py`: `CaptionHistory.pages` 存储问答列表 `[{"question": str, "answer": str}]`
- `ui/main_window.py`: `_on_transcription_ready()` 触发问答流程

现有 `CaptionHistory.pages` 已存储问答序列，但仅用于 UI 展示，未传递给 LLM。

约束：
- PyQt5 信号机制（跨线程通信）
- 配置通过 `config.yaml` 管理
- 不引入新外部依赖

## Goals / Non-Goals

**Goals:**
- 问答历史注入 LLM prompt，实现渐进式回答
- 可配置的历史窗口大小（滑动窗口策略）
- 追问建议生成（可选功能）
- 会话管理（清空历史、开始新会话）

**Non-Goals:**
- 会话持久化到磁盘（本次不做，后续迭代）
- 多会话并行管理
- 云端同步

## Decisions

### 1. 历史存储位置

**决策**: 复用 `ui/overlay_window.py` 的 `CaptionHistory`，不新建模块

**理由**:
- 避免双数据源同步问题
- CaptionHistory 已有完整数据结构和历史管理逻辑
- 所有历史操作在主线程完成（通过 PyQt 信号），不需要额外锁机制

**新增方法**: `CaptionHistory.get_history_for_prompt()` 返回格式化历史

**线程模型**: 保持现有架构 - 所有 `pages` 修改通过 PyQt 信号在主线程完成，无需 `threading.Lock`

**备选方案**:
- A: 复用 CaptionHistory → 无同步问题，推荐
- B: 新建独立模块 → 需同步机制，增加复杂度

### 2. Prompt 注入位置

**决策**: 在系统提示词的**文档信息之后、回答规则之前**插入历史上下文

**Prompt 结构**:
```
[系统提示词基础]
[文档信息（如有）]
[历史对话上下文] ← 新增（放在这里）
[回答规则]
[输出格式]
```

**历史对话格式**:
```
## 前序对话（供参考，理解追问上下文）
Q: <问题1>
A: <回答1摘要>
Q: <问题2>
A: <回答2摘要>
```

**理由**: 历史作为上下文参考，置于文档信息和回答规则之间，既不影响核心指令，又能为回答提供上下文。放在回答规则之前，避免干扰输出格式要求。

### 3. 滑动窗口策略

**决策**: 保留最近 N 条（默认 5），可配置

**配置项**: `conversation.max_history_length: 5`

**理由**:
- 过长历史增加 token 成本、响应延迟
- 5 条覆盖典型追问深度（2-3轮追问）
- 用户可根据面试类型调整

### 4. 追问建议生成方式

**决策**: 独立 LLM 调用，异步生成

**流程**:
1. 主回答完成后，触发追问建议调用
2. 追问建议存入历史模块
3. UI 可选展示（折叠区域）

**理由**:
- 分离主回答与追问建议，避免干扰
- 异步生成，不阻塞主流程
- 用户可选择忽略

**备选方案**:
- A: 同一次调用返回主回答+追问 → prompt 复杂、解析困难
- B: 独立调用 → 清晰分离，推荐

### 5. UI 集成点

**决策**: 
- `MainWindow`: 新增「开始新会话」按钮，清空历史
- `OverlayWindow`: 可选追问建议折叠区域（默认隐藏，配置控制）

**配置项**: `conversation.enable_followup: true`

## Risks / Trade-offs

### Token 成本增加

**风险**: 历史注入增加输入 token，LLM 成本上升

**缓解**: 
- 滑动窗口限制条数
- 回答摘要截断（限制每条回答字数）
- 配置 `conversation.max_history_length` 可关闭历史注入（设为 0）

### 响应延迟

**风险**: 更长 prompt 可能增加首 token 延迟

**缓解**: 
- 监控延迟，动态调整窗口大小
- 提供「快速模式」配置项，禁用历史

### 追问建议质量不稳定

**风险**: LLM 生成的追问可能与实际面试不符

**缓解**: 
- 追问作为参考，非强制
- 配置可关闭追问功能
- 追问建议标注「仅供参考」

## Migration Plan

### 部署步骤

1. 新增 `core/conversation_history.py` 模块
2. 修改 `core/llm_client.py`:
   - `build_system_prompt()` 新增 `history_context` 参数
   - `generate_answer_stream()` 调用时传递历史
3. 修改 `ui/main_window.py`:
   - 初始化 `ConversationHistory` 实例
   - `_on_transcription_ready()` 时更新历史
   - 新增「清空历史」按钮
4. 修改 `config.yaml.template`: 新增配置项

### 回滚策略

- 配置项 `conversation.max_history_length: 0` 立即关闭历史注入
- 追问功能通过 `conversation.enable_followup: false` 关闭
- 无破坏性更改，无需代码回滚

## Open Questions

1. **历史回答摘要长度**: 每条历史回答截断到多少字？（建议 200 字）
2. **追问建议 UI 位置**: Overlay 底部折叠区 or MainWindow 侧边栏？
3. **追问建议触发时机**: 主回答完成后立即生成，or 用户点击「获取追问」按钮？