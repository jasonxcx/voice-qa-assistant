# 面试辅助工具

实时监听会议软件音频，将面试官问题转为文字，通过大模型生成关键点回答并显示字幕。

## 功能特性

- ✅ **系统内录**：通过 WASAPI loopback 捕获腾讯会议/Zoom/Teams 音频
- ✅ **实时 STT**：Faster-Whisper GPU 加速，低延迟转录
- ✅ **大模型**：支持通义千问 API 和本地 Ollama/LM Studio
- ✅ **简历注入**：导入 Markdown 简历，让 AI 更懂你
- ✅ **透明字幕**：PyQt5 叠加窗口，不遮挡视频

## 快速开始

### 1. 安装依赖

```bash
# 安装 PyTorch GPU 支持 (CUDA 11.8)
pip install torch==2.5.1+cu118 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu118

# 安装项目依赖
pip install -r requirements.txt
```

### 2. 配置音频捕获

#### 方案 A：使用 VB-Cable（推荐，音质好）

**安装 VB-Cable:**
1. 下载：https://vb-audio.com/Cable/
2. 安装后重启电脑

**Windows 声音设置:**
1. 右键喇叭 → 声音设置
2. 输出设备：选择 "VB-Cable Input"
3. 输入设备：程序会自动识别

#### 方案 B：使用立体声混音（无需额外软件）

**启用立体声混音:**
1. 右键喇叭 → 声音 → 录制
2. 找到"立体声混音"或"Stereo Mix"
3. 右键 → 启用 → 设为默认设备

### 3. 配置 API Key

编辑 `config.yaml`:
```yaml
llm:
  mode: "qwen"  # 或 "ollama" 或 "lmstudio"
  qwen:
    api_key: "sk-xxx"  # 替换为你的 DashScope API Key
    model: "qwen-max"
```

**获取 API Key:**
- 通义千问：https://dashscope.console.aliyun.com/apiKey

**使用本地模型（免费）:**
```yaml
llm:
  mode: "ollama"
  ollama:
    base_url: "http://localhost:11434"
    model: "qwen2.5:7b"
```

### 4. 运行程序

```bash
python app.py
```

## 使用说明

### 主窗口

1. **简历导入（可选）**
   - 点击"选择 Markdown 简历文件"
   - 选择你的简历文件
   - 不导入则使用通用回答模式

2. **大模型设置**
   - 选择云端（通义千问）或本地（Ollama/LM Studio）
   - 配置相应的 API Key 或 URL

3. **音频设置**
   - 选择音频输入设备
   - 查看实时音量监控

4. **STT 设置**
   - 选择 Whisper 模型（推荐 medium）
   - 选择计算类型（推荐 float32）

5. **控制按钮**
   - ▶ **开始监听**：开始音频捕获和转录
   - 📑 **字幕**：显示/隐藏字幕窗口
   - 📂 **日志**：打开日志文件夹
   - 💾 **保存配置**：保存当前配置

### 字幕窗口

**显示/隐藏:**
- 点击主窗口"📑 字幕"按钮
- 按 **F12** 快捷键

**拖动窗口:**
- 按住顶部灰色拖动条
- 拖动到合适位置

**双击隐藏:**
- 双击顶部灰色拖动条

**字体调节:**
- **Aa-**：缩小字体
- **Aa+**：放大字体
- 档位：16 → 20 → 24 → 28 → 32 → 36 → 40

**翻页查看历史:**
- **◀**：上一条
- **▶**：下一条
- **Ctrl + ←**：上一条（快捷键）
- **Ctrl + →**：下一条（快捷键）

**字幕颜色:**
- 🔵 蓝色：听写中（实时转录）
- 🟢 绿色：回答（AI 生成的回答）
- ⚪ 白色：普通文本
- 🔴 红色：错误

## 项目结构

```
interview-helper/
├── app.py                # 主程序入口
├── config.yaml           # 配置文件
├── requirements.txt      # Python 依赖
├── README.md            # 使用说明
├── core/                # 核心模块
│   ├── config.py        # 配置管理
│   ├── audio_capture.py # 音频捕获（RealtimeSTT）
│   ├── llm_client.py    # 大模型客户端
│   ├── resume_parser.py # 简历解析
│   └── logger.py        # 日志模块
├── ui/                  # 界面模块
│   ├── main_window.py   # 主窗口
│   ├── overlay_window.py # 字幕窗口
│   └── styles.py        # 样式表
└── logs/                # 日志文件夹
    ├── stt.log         # STT 转录日志
    ├── llm.log         # LLM 问答日志
    └── system.log      # 系统日志
```

## 配置说明

### config.yaml

```yaml
# 大模型配置
llm:
  mode: "qwen"  # qwen/ollama/lmstudio
  qwen:
    api_key: "sk-xxx"
    model: "qwen-max"
  ollama:
    base_url: "http://localhost:11434"
    model: "qwen2.5:7b"

# 音频配置
audio:
  input_device_index: -1  # -1 表示自动选择
  use_microphone: false   # false 为系统内录

# STT 配置
stt:
  local:
    model: "medium"       # tiny/base/small/medium/large-v2
    device: "cuda"        # cuda/cpu
    language: "zh"        # zh/en
    compute_type: "float32"

# UI 配置
ui:
  font_size: 28           # 字幕字体大小
  overlay_height: 140     # 字幕窗口高度
  overlay_width_ratio: 0.85  # 字幕窗口宽度比例
```

## 常见问题

### Q: 字幕窗口不显示？
A: 点击主窗口"📑 字幕"按钮或按 F12 显示。

### Q: 听不到声音/无法转录？
A: 检查音频设备设置：
1. 确保 VB-Cable 已正确安装
2. Windows 输出设备设置为 VB-Cable Input
3. 或者启用立体声混音

### Q: 转录延迟高？
A: 尝试以下优化：
1. 使用 GPU 加速（确保 CUDA 已安装）
2. 使用较小的 Whisper 模型（tiny/base）
3. 检查音频设备采样率设置

### Q: 字幕窗口遮挡会议视频？
A: 拖动窗口顶部灰色条移动位置，或调整窗口大小。

### Q: 如何查看日志？
A: 点击主窗口"📂 日志"按钮，或打开 `logs/` 文件夹。

## 依赖说明

| 依赖 | 用途 |
|------|------|
| PyQt5 | 图形界面 |
| RealtimeSTT | 实时语音转文字 |
| faster-whisper | Whisper 模型推理 |
| sounddevice | 音频设备查询 |
| pyaudiowpatch | WASAPI loopback 音频捕获 |
| dashscope | 通义千问 API |
| openai | 兼容 Ollama/LM Studio |
| mistune | Markdown 简历解析 |

## 技术原理

### 音频捕获流程

```
会议软件 → VB-Cable → WASAPI Loopback → RealtimeSTT → 转录文字
                                    ↓
                              Faster-Whisper (GPU 加速)
```

### 字幕显示流程

```
转录文字 → LLM 客户端 → 生成回答 → PyQt5 字幕窗口
            ↓
      简历信息注入
```

## 更新日志

### v1.0
- ✅ 初始版本发布
- ✅ 支持 WASAPI loopback 音频捕获
- ✅ 支持通义千问/Ollama/LM Studio
- ✅ 透明字幕窗口
- ✅ Markdown 简历解析
- ✅ 实时音量监控

## 许可证

MIT License

## 反馈与支持

如有问题或建议，请提交 Issue 或联系开发者。
