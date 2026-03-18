# 面试辅助工具

实时监听会议软件音频，将面试官问题转为文字，通过大模型生成关键点回答并显示字幕。

## 功能特性

- ✅ 系统内录：捕获腾讯会议/Zoom/Teams 音频
- ✅ 实时 STT：Faster-Whisper GPU 加速，<3 秒延迟
- ✅ 大模型：支持通义千问 API 和本地 Ollama/LM Studio
- ✅ 简历注入：导入 Markdown 简历，让 AI 更懂你
- ✅ 透明字幕：PyQt5 叠加窗口，不遮挡视频

## 快速开始

### 1. 安装依赖

```bash
# 安装 PyTorch GPU 支持 (CUDA 11.8)
pip install torch==2.5.1+cu118 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu118

# 安装项目依赖
pip install -r requirements.txt
```

### 2. 配置 VB-Cable 系统内录

**安装 VB-Cable:**
1. 下载：https://vb-audio.com/Cable/
2. 安装后重启电脑

**Windows 声音设置:**
1. 右键喇叭图标 → 声音设置
2. 输出设备：选择 "VB-Cable Input"
3. 输入设备：选择 "VB-Cable Output"

**查看设备索引:**
```bash
python -m sounddevice
```
记录 VB-Cable 的索引号，填入 `config.yaml` 的 `audio.input_device_index`

### 3. 配置 API Key

编辑 `config.yaml`:
```yaml
llm:
  mode: "qwen"
  qwen:
    api_key: "sk-xxx"  # 替换为你的 DashScope API Key
```

或使用本地 Ollama:
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

1. **导入简历**: 点击"选择简历"按钮，选择 Markdown 格式的简历文件
2. **选择模式**: 选择云端 (Qwen) 或本地 (Ollama) 模式
3. **开始监听**: 点击"开始"按钮，程序开始监听音频
4. **查看字幕**: 屏幕底部会显示转录问题和 AI 回答关键点

## 快捷键

- `F1`: 显示/隐藏字幕窗口
- `F2`: 开始/暂停监听
- `Esc`: 退出程序

## 故障排除

**字幕窗口不显示:**
- 检查是否被其他窗口遮挡，尝试最小化其他窗口
- 确认屏幕分辨率设置

**无法捕获音频:**
- 确认 VB-Cable 已正确安装
- 检查 Windows 声音输入/输出设备设置
- 确认 `config.yaml` 中的 `input_device_index` 正确

**STT 延迟高:**
- 确认 GPU 驱动已安装
- 尝试使用更小的 Whisper 模型 (base/tiny)

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
│   ├── resume_parser.py  # 简历解析
│   └── config.py         # 配置管理
├── requirements.txt
├── config.yaml
└── README.md
```
