# 实时问答助理

实时监听会议软件音频并转为文字，再通过LLM大模型生成答复并显示字幕。

## 功能特性

- ✅ 系统内录：捕获腾讯会议/Zoom/Teams 音频
- ✅ 实时 STT：Faster-Whisper GPU 加速，<3 秒延迟
- ✅ 大模型：支持通义千问 API 和本地 Ollama/LM Studio
- ✅ 文本注入：导入 Markdown 文本知识库，让 AI 更懂你
- ✅ 透明字幕：PyQt5 叠加窗口，不遮挡视频

## 项目结构

```
interview-helper/
├── app.py                # 主程序入口
├── ui/
│   ├── main_window.py    # 主窗口
│   ├── overlay_window.py # 字幕窗口
│   └── styles.py         # 样式表
├── core/
│   ├── audio_capture.py  # 音频捕获
│   ├── llm_client.py     # 大模型客户端
│   ├── resume_parser.py  # markdown文档解析
│   ├── logger.py         # 日志管理
│   └── config.py         # 配置管理
├── requirements.txt
├── config.yaml
└── README.md
```

## 快速开始

### 1. 环境配置

```bash
# （可选）配置虚拟环境，要求python > 3.10
conda create -n py311 python=3.11 -y
conda activate py311

# 安装项目依赖
pip install -r requirements.txt

# 安装 PyTorch GPU 支持 (CUDA 11.8)
pip install torch==2.5.1+cu118 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu118

# 安装 PyTorch GPU 支持 (CUDA 12.8)
pip install torch==2.7.1+cu128 torchaudio==2.7.1+cu128 --index-url https://download.pytorch.org/whl/cu128
```

### 2. 配置 API Key

由 `config.yaml.template` 创建一份 `config.yaml`，并修改llm的配置
```yaml
llm:
  mode: openai
  base_url: https://coding.dashscope.aliyuncs.com/v1 # 百炼Coding Plan计划
  api_key: sk-xxx  # 替换为你的 DashScope API Key
  model: qwen-max
```

或使用本地 Ollama / LM Studio:
```yaml
llm:
  mode: "lmstudio" # 或者 
  base_url: "http://127.0.0.1:1234"
  model: "qwen3.5-4b"
```

### 3. 运行程序

```bash
python app.py
```

## 使用说明

1. **导入文档**: 点击"选择文档"按钮，选择 Markdown 格式的文件
2. **模型配置**: 配置 LLM 模型和 STT 模型
3. **开始**: 点击"加载模型"按钮，屏幕底部会显示字幕窗口，可以手动点击按钮开始监听音频
4. **查看字幕**: 点击结束监听按钮后程序会转录问题和 AI 回答关键点

### 快捷键

可以在配置文件里面进行配置

| 名称        | 默认快捷键       | 功能配置项                |
|:----------|:------------|----------------------|
| 显示/隐藏字幕窗口 | **Ctrl+F4** | `overlay_visibility` |
| 切换自动/手动模式 | **Ctrl+F6** | `transcription_mode` |
| 开始/结束监听   | **Ctrl+F8** | `listening_toggled`  |
| 上一条字幕记录   | **Ctrl+F7** | `prev_caption`       |
| 下一条字幕记录   | **Ctrl+F9** | `next_caption`       |

## 故障排除

**字幕窗口不显示:**
- 检查是否被其他窗口遮挡，尝试最小化其他窗口
- 确认屏幕分辨率设置

**无法捕获音频:**
- 确认输入设备
- 检查 Windows 声音输入/输出设备设置

**STT 延迟高:**
- 确认 GPU 驱动已安装、确认安装 cuda
- 尝试使用更小的 Whisper 模型 (base/tiny)

## 注意事项

在线会议等软件的屏幕共享功能（如果你不想让别人看到本工具）：
- UI界面：使用[shalzuth/WindowSharingHider](https://github.com/shalzuth/WindowSharingHider)，我放在 [ui/WindowSharingHider.exe](ui/WindowSharingHider.exe) 目录中，可以直接点开使用。
- 任务栏：直接使用windows自带的任务栏隐藏功能，或者干脆把任务栏移到第二个显示器

## 免责声明 / Disclaimer

本项目仅供技术学习与研究交流之用，严禁用于以下用途：
- 任何形式的求职面试作弊行为
- 侵犯他人隐私或商业秘密
- 违反当地法律法规的行为

使用者应对自身行为负全部法律责任，作者不承担任何因滥用本项目导致的直接或间接后果。使用即表示您已阅读并同意本声明。