"""
主窗口 - 简历导入、配置、控制
"""

import asyncio
import datetime
import logging
import os
import threading
import time
from typing import Any, Dict, List, Optional

import requests
import sounddevice as sd
from PyQt5.QtCore import Qt, QTimer, pyqtSlot, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.logger import log_llm, log_system
from core.resume_parser import parse_resume
from ui.styles import MAIN_WINDOW_STYLESHEET, STATUS_COLORS


class MainWindow(QMainWindow):
    """主窗口"""

    # 信号用于线程间通信
    token_signal = pyqtSignal(str, int)  # token, page_index
    complete_signal = pyqtSignal(str)    # answer
    error_signal = pyqtSignal(str)       # error_msg

    def __init__(self, overlay_window, audio_capture, llm_client):
        super().__init__()
        self.overlay = overlay_window
        self.audio_capture = audio_capture
        self.llm_client = llm_client
        self.config = audio_capture.config
        
        self.resume_data: Optional[Dict[str, Any]] = None
        self.audio_devices: List[Dict] = []
        self.is_model_loading = False
        
        self._init_ui()
        print("[Debug] _init_ui 完成", flush=True)
        self._connect_signals()
        print("[Debug] _connect_signals 完成", flush=True)
        self._load_audio_devices()
        print("[Debug] _load_audio_devices 完成", flush=True)
        self._sync_ui_with_config()
        print("[Debug] _sync_ui_with_config 完成", flush=True)

        # 启动音量监控（独立于录音）
        self.audio_capture.start_monitoring()
        self._initialized = True
        print("[Debug] MainWindow 初始化完成", flush=True)
    
    def _init_ui(self):
        """初始化 UI"""

        
        # 从配置读取图标路径，如果配置为空或文件不存在则不设置图标
        icon_path = self.config.icon_path
        if icon_path and os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        self.setMinimumSize(500, 550)
        self.setStyleSheet(MAIN_WINDOW_STYLESHEET)
        
        # 中央控件
        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # 状态标签
        self.status_label = QLabel("● 就绪")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # 简历导入
        resume_group = QGroupBox("简历导入（可选）")
        resume_layout = QVBoxLayout(resume_group)
        
        self.resume_path_label = QLabel("未选择简历文件（将使用通用回答模式）")
        self.resume_path_label.setStyleSheet("color: #9AA0A6; padding: 8px;")
        resume_layout.addWidget(self.resume_path_label)
        
        select_btn = QPushButton(" 选择 Markdown 简历文件")
        select_btn.clicked.connect(self._select_resume)
        resume_layout.addWidget(select_btn)
        
        layout.addWidget(resume_group)
        
        # 大模型设置
        llm_group = QGroupBox("大模型设置")
        llm_layout = QVBoxLayout(llm_group)
        
        llm_form = QFormLayout()
        self.llm_combo = QComboBox()
        self.llm_combo.addItems(["OpenAI (云端)", "Ollama（本地）", "LM Studio (本地)"])
        self.llm_combo.currentIndexChanged.connect(self._on_llm_changed)
        llm_form.addRow("模型模式:", self.llm_combo)

        # 模型名称输入框
        self.model_name_input = QLineEdit()
        self.model_name_input.setPlaceholderText("如：qwen3.5-plus, qwen2.5:7b")
        self.model_name_input_label = QLabel("模型名称:")
        llm_form.addRow(self.model_name_input_label, self.model_name_input)

        # 模型Url输入框
        self.llm_url = QLineEdit()
        self.llm_url.setPlaceholderText("http://localhost")

        # LM Studio 模型刷新按钮和下拉框
        self.refresh_models_btn = QPushButton("🔄 刷新模型列表")
        self.refresh_models_btn.setToolTip("从 LM Studio 获取可用模型")
        self.refresh_models_btn.setFixedHeight(28)
        self.refresh_models_btn.clicked.connect(self._refresh_lmstudio_models)
        self.refresh_models_btn.setEnabled(False)

        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)  # 可编辑，也可以手动输入
        self.model_combo.setToolTip("从 LM Studio 选择模型（鼠标悬停查看参数）")
        self.model_combo.setEnabled(False)  # 默认禁用
        self.model_combo.currentIndexChanged.connect(self._on_model_combo_changed)

        # 使用 QHBoxLayout 将刷新按钮和下拉框放在同一行
        self.model_combo_layout = QHBoxLayout()
        self.model_combo_layout.setSpacing(4)
        self.model_combo_layout.addWidget(self.model_combo)
        self.model_combo_layout.addWidget(self.refresh_models_btn)
        self.model_combo_label = QLabel("选择模型:")
        llm_form.addRow(self.model_combo_label, self.model_combo_layout)
        
        llm_layout.addLayout(llm_form)
        layout.addWidget(llm_group)
        
        # 音频和音量（合并为一组）
        audio_group = QGroupBox("音频设置")
        audio_layout = QVBoxLayout(audio_group)
        
        audio_form = QFormLayout()
        
        # 音频设备
        self.audio_device_combo = QComboBox()
        audio_form.addRow("输入设备:", self.audio_device_combo)
        
        # 音量监控
        self.volume_bar = QLabel()
        self.volume_bar.setMinimumHeight(20)
        self.volume_bar.setStyleSheet("background-color: #2D2D2D; border-radius: 4px;")
        audio_form.addRow("音量:", self.volume_bar)
        
        self.volume_label = QLabel("音量：0%")
        self.volume_label.setStyleSheet("color: #9AA0A6; font-size: 11px;")
        audio_form.addRow("", self.volume_label)
        
        audio_layout.addLayout(audio_form)
        layout.addWidget(audio_group)
        
        # STT 设置
        stt_group = QGroupBox("语音识别 (STT) 设置")
        stt_layout = QVBoxLayout(stt_group)
        
        stt_form = QFormLayout()
        
        self.stt_model_combo = QComboBox()
        self.stt_model_combo.addItems(
            [
                "tiny (75MB, 最快)",
                "base (143MB, 快)",
                "small (467MB, 平衡)",
                "medium (1.5GB, 推荐)",
                "large-v2 (2.9GB, 最准确)",
                "large-v3 (3GB, 最新)"
            ]
        )
        self.stt_model_combo.setCurrentIndex(3)
        stt_form.addRow("模型:", self.stt_model_combo)

        self.stt_device_combo = QComboBox()
        self.stt_device_combo.addItems(["CPU", "CUDA (GPU)"])
        self.stt_device_combo.setCurrentIndex(1)  # 默认使用 GPU
        stt_form.addRow("计算设备:", self.stt_device_combo)

        self.compute_type_combo = QComboBox()
        self.compute_type_combo.addItems(["float32 (兼容)", "float16 (快速)", "int8 (省显存)"])
        self.compute_type_combo.setCurrentIndex(0)
        stt_form.addRow("计算类型:", self.compute_type_combo)
        
        stt_layout.addLayout(stt_form)
        layout.addWidget(stt_group)
        
        # 控制按钮（一行）
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        
        self.start_btn = QPushButton("▶ 加载模型")
        self.start_btn.setMinimumHeight(45)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078D4;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1084D8;
            }
        """)
        self.start_btn.clicked.connect(self._toggle_listening)
        button_layout.addWidget(self.start_btn)
        
        # 字幕窗口显示/隐藏按钮
        self.caption_toggle_btn = QPushButton("📑 字幕")
        self.caption_toggle_btn.setMinimumHeight(45)
        self.caption_toggle_btn.setToolTip("显示/隐藏字幕窗口 (F12)")
        self.caption_toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #2D2D2D;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #3D3D3D;
            }
        """)
        self.caption_toggle_btn.clicked.connect(self._toggle_caption_window)
        button_layout.addWidget(self.caption_toggle_btn)
        
        self.log_btn = QPushButton("📂 日志")
        self.log_btn.setMinimumHeight(45)
        self.log_btn.setStyleSheet(self.caption_toggle_btn.styleSheet())
        self.log_btn.clicked.connect(self._open_log_folder)
        button_layout.addWidget(self.log_btn)
        
        self.save_btn = QPushButton("💾 保存配置")
        self.save_btn.setMinimumHeight(45)
        self.save_btn.setStyleSheet(self.caption_toggle_btn.styleSheet())
        self.save_btn.clicked.connect(self._save_config)
        button_layout.addWidget(self.save_btn)
        
        layout.addLayout(button_layout)

        # 字幕状态
        self.caption_status = QLabel("字幕窗口：未显示（点击后显示/隐藏，拖动顶部灰色条移动窗口）")
        self.caption_status.setStyleSheet("color: #9AA0A6; font-size: 11px;")
        layout.addWidget(self.caption_status)

        # 转录日志区域
        log_group = QGroupBox("转录日志")
        log_layout = QVBoxLayout(log_group)

        # 转录日志文本框
        self.transcription_log = QTextEdit()
        self.transcription_log.setReadOnly(True)
        self.transcription_log.setMaximumHeight(150)
        self.transcription_log.setStyleSheet("""
            QTextEdit {
                background-color: #1E1E1E;
                color: #9AA0A6;
                border: 1px solid #2D2D2D;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
            }
        """)
        self.transcription_log.setPlaceholderText("转录的问题将显示在这里...")
        log_layout.addWidget(self.transcription_log)

        # 日志控制按钮
        log_control_layout = QHBoxLayout()
        self.clear_log_btn = QPushButton("清空日志")
        self.clear_log_btn.setFixedHeight(28)
        self.clear_log_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 100, 100, 100);
                color: #FFFFFF;
                border: none;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(255, 100, 100, 150);
            }
        """)
        self.clear_log_btn.clicked.connect(self._clear_transcription_log)
        log_control_layout.addWidget(self.clear_log_btn)
        log_control_layout.addStretch()
        log_layout.addLayout(log_control_layout)

        layout.addWidget(log_group)

        self._update_ui_state()
    
    def _load_audio_devices(self):
        """加载音频设备列表"""
        try:
            devices = sd.query_devices()
            self.audio_devices = []
            self.audio_device_combo.clear()
            
            for i, dev in enumerate(devices):
                if dev['max_input_channels'] > 0:
                    device_name = f"{i}: {dev['name'][:40]} (通道:{dev['max_input_channels']})"
                    self.audio_device_combo.addItem(device_name)
                    self.audio_devices.append({
                        'index': i,
                        'name': dev['name'],
                        'channels': dev['max_input_channels']
                    })
            
        except Exception as e:
            QMessageBox.warning(self, "设备扫描失败", f"无法获取音频设备列表：{e}")
            self.audio_device_combo.addItem("1: 默认设备")
            self.audio_devices = [{'index': 1, 'name': '默认设备', 'channels': 2}]
    
    def _sync_ui_with_config(self):
        """将配置同步到 UI"""
        print(f"[Debug] _sync_ui_with_config 开始, config.llm_mode={self.config.llm_mode}", flush=True)
        mode_map = {"openai": 0, "ollama": 1, "lmstudio": 2}
        # 阻止信号触发，避免在初始化时调用 _refresh_lmstudio_models
        self.llm_combo.blockSignals(True)
        self.llm_combo.setCurrentIndex(mode_map.get(self.config.llm_mode, 0))
        self.llm_combo.blockSignals(False)

        self.llm_url.setText(self.config.llm_base_url)
        self.model_name_input.setText(self.config.llm_model)

        # 根据当前模式设置 UI 可见性
        is_lmstudio = (self.config.llm_mode == "lmstudio")
        print(f"[Debug] is_lmstudio={is_lmstudio}", flush=True)

        # OpenAI/Ollama 模式：只显示模型名称输入框
        # LM Studio 模式：只显示模型选择下拉框和刷新按钮
        self.model_name_input_label.setVisible(not is_lmstudio)
        self.model_name_input.setVisible(not is_lmstudio)
        self.model_combo_label.setVisible(is_lmstudio)
        self.model_combo.setVisible(is_lmstudio)
        self.refresh_models_btn.setVisible(is_lmstudio)
        self.model_combo.setEnabled(is_lmstudio)
        self.refresh_models_btn.setEnabled(is_lmstudio)

        model_map = {"tiny": 0, "base": 1, "small": 2, "medium": 3, "large-v2": 4, "large-v3": 5}
        self.stt_model_combo.setCurrentIndex(model_map.get(self.config.stt_model, 3))

        # 同步 STT 设备选择
        device_map = {"cpu": 0, "cuda": 1, "gpu": 1}
        stt_device = self.config.get("stt.local.device", "cuda").lower()
        self.stt_device_combo.setCurrentIndex(device_map.get(stt_device, 1))

        compute_map = {"float32": 0, "float16": 1, "int8": 2}
        self.compute_type_combo.setCurrentIndex(compute_map.get(self.config.get("stt.local.compute_type", "float32"), 0))

        for idx, dev in enumerate(self.audio_devices):
            if dev['index'] == self.config.audio_device_index:
                self.audio_device_combo.setCurrentIndex(idx)
                break

    def _connect_signals(self):
        """连接信号"""
        self.audio_capture.transcription_ready.connect(self._on_transcription_ready)
        self.audio_capture.real_time_update.connect(self._on_realtime_update)
        self.audio_capture.recording_started.connect(self._on_recording_started)
        self.audio_capture.recording_stopped.connect(self._on_recording_stopped)
        self.audio_capture.error_occurred.connect(self._on_error)
        self.audio_capture.volume_update.connect(self._on_volume_update)
        self.audio_capture.model_loading_started.connect(self._on_model_loading_started)
        self.audio_capture.model_loaded.connect(self._on_model_loaded)
        self.audio_capture.model_unloaded.connect(self._on_model_unloaded)

        # 连接 overlay 窗口的显示/隐藏信号
        self.overlay.visibilityChanged.connect(self._on_overlay_visibility_changed)
        
        # 连接 overlay 的监听控制信号
        self.overlay.listeningStarted.connect(self._on_overlay_listening_started)
        self.overlay.listeningStopped.connect(self._on_overlay_listening_stopped)

        # 连接 LLM 信号到槽函数
        self.token_signal.connect(self._on_token_update)
        self.complete_signal.connect(self._on_generation_complete)
        self.error_signal.connect(self._on_llm_error_slot)

        self.volume_timer = QTimer()
        self.volume_timer.timeout.connect(self._update_volume_display)
        self.volume_timer.start(100)

        self.caption_queue = []
        self.current_volume = 0.0
    
    def _select_resume(self):
        """选择简历文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择简历文件", "", "Markdown 文件 (*.md);;所有文件 (*.*)"
        )
        
        if file_path:
            try:
                self.resume_data = parse_resume(file_path)
                self.resume_path_label.setText(f"[OK] {file_path}")
                self.resume_path_label.setStyleSheet("color: #4CAF50; padding: 8px;")
                
                summary = f"已解析：{self.resume_data.get('name', '未知')} | "
                summary += f"技能：{len(self.resume_data.get('skills', []))} 项 | "
                summary += f"经历：{len(self.resume_data.get('experience', []))} 段"
                self.resume_path_label.setToolTip(summary)
                
            except Exception as e:
                QMessageBox.critical(self, "解析失败", f"简历解析失败：{str(e)}")
    
    def _on_llm_changed(self, index: int):
        """切换 LLM 模式"""
        print(f"[Debug] _on_llm_changed 被调用，index={index}", flush=True)
        mode_map = {0: "openai", 1: "ollama", 2: "lmstudio"}
        self.config.switch_llm_from_file(mode_map.get(index, "openai"))

        # 更新模型信息
        self.llm_url.setText(self.config.llm_base_url)
        self.model_name_input.setText(self.config.llm_model)
        
        # 启用/禁用 LM Studio 模型刷新按钮和下拉框
        is_lmstudio = (index == 2)

        # OpenAI/Ollama 模式：显示模型名称输入框，隐藏模型选择下拉框
        self.model_name_input_label.setVisible(not is_lmstudio)
        self.model_name_input.setVisible(not is_lmstudio)
        self.model_combo_label.setVisible(is_lmstudio)
        self.model_combo.setVisible(is_lmstudio)
        self.refresh_models_btn.setVisible(is_lmstudio)

        # 启用/禁用
        self.model_combo.setEnabled(is_lmstudio)
        self.refresh_models_btn.setEnabled(is_lmstudio)
        
        # 切换到 LM Studio 模式时自动刷新模型列表（仅在用户手动切换时）
        # 初始化时的刷新在 _sync_ui_with_config 中处理
        if is_lmstudio and hasattr(self, '_initialized'):
            self._refresh_lmstudio_models()
        
        try:
            self.llm_client.switch_mode()
            self._update_ui_state()
        except Exception as e:
            QMessageBox.critical(self, "切换失败", str(e))
    
    def _toggle_listening(self):
        """切换监听状态"""
        if self.audio_capture.is_running():
            # 停止监听
            print("[主窗口] 正在停止监听...", flush=True)
            self.status_label.setText("● 停止中...")
            self.status_label.setStyleSheet(f"color: {STATUS_COLORS['generating']};")
            self.audio_capture.stop()
            self.overlay.hide()
            self.caption_status.setText("字幕窗口：已隐藏（点击字幕按钮或 F12 重新显示）")
            self.caption_toggle_btn.setText("📑 字幕")
            self._update_ui_state()
            print("[主窗口] 监听已停止", flush=True)
        else:
            print("[主窗口] 正在加载模型并开始监听...", flush=True)
            self.status_label.setText("● 加载模型中...")
            self.status_label.setStyleSheet(f"color: {STATUS_COLORS['generating']};")
            self._update_config_from_ui()
            
            is_valid, error_msg = self.config.validate()
            if not is_valid:
                QMessageBox.warning(self, "配置错误", error_msg)
                return
            
            self.audio_capture.start()
            self._update_ui_state()
    
    def _toggle_caption_window(self):
        """切换字幕窗口显示/隐藏"""
        if self.overlay.isVisible():
            self.overlay.hide()
            self.caption_status.setText("字幕窗口：已隐藏（点击字幕按钮或 F12 重新显示）")
            self.caption_toggle_btn.setText("📑 字幕")
        else:
            self.overlay.show()
            self.caption_status.setText("字幕窗口：显示中（拖动顶部灰色条移动窗口，双击隐藏）")
            self.caption_toggle_btn.setText("📑 隐藏")
    
    def _refresh_lmstudio_models(self):
        """从 LM Studio 获取模型列表（使用/api/v1/models 接口）"""
        # 检查 self 是否仍然有效
        if not self or not hasattr(self, "config"):
            print("[Debug] _refresh_lmstudio_models: self 已被释放，退出", flush=True)
            return

        if self.config.llm_mode != "lmstudio":
            return

        print("[Debug] _refresh_lmstudio_models 开始")
        self.refresh_models_btn.setText("⏳ 获取中...")
        self.refresh_models_btn.setEnabled(False)

        def fetch_models():
            models = []  # 初始化 models 变量
            try:
                base_url = self.config.llm_base_url.rstrip('/')
                if not base_url:
                    base_url = "http://localhost:1234"

                print(f"[Debug] 请求 LM Studio API: {base_url}/api/v1/models")
                # 使用 LM Studio 的/api/v1/models 接口获取详细信息
                response = requests.get(f"{base_url}/api/v1/models", timeout=5)
                print(f"[Debug] 响应状态码：{response.status_code}")

                if response.status_code == 200:
                    data = response.json()
                    print(f"[Debug] 响应数据 keys: {data.keys()}")
                    # LM Studio 返回格式：{"models": [{"type": "llm", "key": "...", "display_name": "...", ...}, ...]}
                    models_data = data.get("models", [])
                    print(f"[Debug] models_data 数量：{len(models_data)}")
                    # 过滤 LLM 类型并转换为统一格式（保留 loaded_instances 用于获取 context_length）
                    models = []
                    for model in models_data:
                        if model.get("type") == "llm":
                            models.append({
                                "key": model.get("key", "unknown"),
                                "display_name": model.get("display_name", model.get("key", "unknown")),
                                "max_context_length": model.get("max_context_length"),
                                "size_bytes": model.get("size_bytes"),
                                "quantization": model.get("quantization", {}),
                                "architecture": model.get("architecture"),
                                "loaded_instances": model.get("loaded_instances", []),  # 保留 loaded_instances
                            })
                    print(f"从 LM Studio 成功获取到 {len(models)} 个模型供选择")
                else:
                    print(f"从 LM Studio 获取模型失败，状态码：{response.status_code}")
            except Exception as e:
                print(f"从 LM Studio 获取模型时发生错误：{e}")
                import traceback
                traceback.print_exc()
            finally:
                print(f"[Debug] finally 块，models 数量={len(models)}")
                print(f"[Debug] 调用 _update_model_combo (models={len(models)})")
                # 直接更新 UI（在主线程中）
                self._update_model_combo(models)

        print("[Debug] 启动线程")
        threading.Thread(target=fetch_models, daemon=True).start()

    def _update_model_combo(self, models: List[Dict]):
        """更新模型下拉框（带详细信息）"""
        print(f"[Debug] _update_model_combo 开始，models={len(models)}", flush=True)
        print(f"[Debug] 清空下拉框", flush=True)
        self.model_combo.clear()
        print(f"[Debug] 下拉框已清空", flush=True)

        # 获取当前配置的模型名称
        current_config_model = self.config.llm_model
        print(f"[Debug] 当前配置的模型: {current_config_model}", flush=True)

        # 分离有 loaded_instances 和没有的模型
        loaded_models = []
        not_loaded_models = []
        for model in models:
            if model.get("loaded_instances"):
                loaded_models.append(model)
            else:
                not_loaded_models.append(model)

        print(f"[Debug] 有加载实例的模型: {len(loaded_models)}, 未加载的模型: {len(not_loaded_models)}", flush=True)

        # 构建模型列表：有 loaded_instances 的在前
        ordered_models = loaded_models + not_loaded_models

        # 用于匹配的字典
        model_map = {}  # key -> model
        display_name_map = {}  # display_name -> model
        for model in ordered_models:
            key = model.get("key", "unknown")
            display_name = model.get("display_name", key)
            model_map[key] = model
            if display_name not in display_name_map:
                display_name_map[display_name] = model

        # 设置下拉框项
        selected_index = -1
        for model in ordered_models:
            key = model.get("key", "unknown")
            display_name = model.get("display_name", key)
            loaded_instances = model.get("loaded_instances", [])

            # 构建提示信息
            tooltip_parts = []

            # 上下文长度
            max_context = model.get("max_context_length")
            if max_context:
                tooltip_parts.append(f"最大上下文：{max_context:,} tokens")

            # 已加载实例信息
            if loaded_instances:
                for instance in loaded_instances:
                    config = instance.get("config", {})
                    context_length = config.get("context_length")
                    if context_length:
                        tooltip_parts.append(f"运行时上下文：{context_length:,} tokens")
                        break

            # 模型大小
            size_bytes = model.get("size_bytes")
            if size_bytes:
                size_gb = size_bytes / (1024 ** 3)
                tooltip_parts.append(f"模型大小：{size_gb:.2f} GB")

            # 量化信息
            quantization = model.get("quantization", {})
            if quantization:
                name = quantization.get("name")
                bits = quantization.get("bits_per_weight")
                if name and bits:
                    tooltip_parts.append(f"量化：{name} ({bits}bit)")

            tooltip = "\n".join(tooltip_parts) if tooltip_parts else "无详细信息"

            # 设置显示文本（有 loaded_instances 的加标记）
            if loaded_instances:
                display_text = f"{display_name} ({key}) ✓"
            else:
                display_text = f"{display_name} ({key})"

            # 添加模型到下拉框
            index = self.model_combo.count()
            self.model_combo.addItem(display_text, key)
            self.model_combo.setItemData(index, tooltip, Qt.ToolTipRole)

            # 设置有 loaded_instances 的模型颜色
            if loaded_instances:
                from PyQt5.QtGui import QColor, QBrush
                self.model_combo.setItemData(index, QBrush(QColor("#4CAF50")), Qt.ForegroundRole)
                self.model_combo.setItemData(index, "有加载实例的模型", Qt.ToolTipRole)

            # 检查是否匹配当前配置的模型
            if selected_index == -1:
                # 优先匹配 key，其次匹配 display_name
                if key == current_config_model or display_name == current_config_model:
                    selected_index = index
                    print(f"[Debug] 匹配到配置模型: {display_text}", flush=True)
                # 如果没有匹配，尝试匹配不带版本号的模型名
                elif current_config_model in key or current_config_model in display_name:
                    selected_index = index
                    print(f"[Debug] 部分匹配配置模型: {display_text}", flush=True)

        # 设置选中项（阻止信号触发，避免循环调用）
        self.model_combo.blockSignals(True)
        if selected_index >= 0:
            self.model_combo.setCurrentIndex(selected_index)
            print(f"[Debug] 选中索引: {selected_index}", flush=True)
        elif self.model_combo.count() > 0:
            # 如果没有匹配到，选中第一个有 loaded_instances 的模型
            for i in range(self.model_combo.count()):
                item_data = self.model_combo.itemData(i, Qt.ToolTipRole)
                if item_data and "有加载实例" in str(item_data):
                    self.model_combo.setCurrentIndex(i)
                    print(f"[Debug] 默认选中第一个有加载实例的模型，索引: {i}", flush=True)
                    break
            else:
                # 如果没有有加载实例的模型，选中第一个
                self.model_combo.setCurrentIndex(0)
                print(f"[Debug] 默认选中第一个模型，索引: 0", flush=True)
        self.model_combo.blockSignals(False)

        self.refresh_models_btn.setText("🔄 刷新模型列表")
        print(f"[Debug] 设置刷新按钮文本为重试", flush=True)

        print(f"[Debug] _update_model_combo 完成1", flush=True)
        print(f"[Debug] _update_model_combo 完成，设置了 {len(models)} 个模型", flush=True)
        print(f"[Debug] _update_model_combo 完成2", flush=True)
        self.refresh_models_btn.setEnabled(True)

        from PyQt5.QtCore import QTimer
        QTimer.singleShot(3000, lambda: self.refresh_models_btn.setText("🔄 刷新模型列表"))

    def _update_model_combo_simple(self, models: List[Dict]):
        """更新模型下拉框（简化版，用于 LM Studio）"""
        self.model_combo.clear()

        if models:
            for model in models:
                key = model.get("key", "unknown")
                display_name = model.get("display_name", key)
                self.model_combo.addItem(display_name, key)
            self.refresh_models_btn.setText("🔄 刷新模型列表")
        else:
            self.model_combo.addItem("未找到模型（请确保 LM Studio 已启动并加载模型）", "")
            self.refresh_models_btn.setText("🔄 重试")
        self.refresh_models_btn.setEnabled(True)
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(3000, lambda: self.refresh_models_btn.setText("🔄 刷新模型列表"))


    
    def _on_model_combo_changed(self, index: int):
        """模型选择变化时更新配置"""
        if self.config.llm_mode != "lmstudio":
            return
        
        model_key = self.model_combo.itemData(index)
        if model_key:
            self.config.set("llm.model", model_key)
    
    def _update_config_from_ui(self):
        """从 UI 更新配置 - 更新临时配置和 provider 永久配置"""
        model_map = {0: "tiny", 1: "base", 2: "small", 3: "medium", 4: "large-v2", 5: "large-v3"}
        stt_model = model_map.get(self.stt_model_combo.currentIndex(), "medium")
        self.config.set("stt.model", stt_model)

        # 更新 STT 设备选择
        device_map = {0: "cpu", 1: "cuda"}
        stt_device = device_map.get(self.stt_device_combo.currentIndex(), "cuda")
        self.config.set("stt.local.device", stt_device)

        compute_map = {0: "float32", 1: "float16", 2: "int8"}
        compute_type = compute_map.get(self.compute_type_combo.currentIndex(), "float32")
        self.config.set("stt.local.compute_type", compute_type)

        # 安全获取音频设备索引，避免越界
        current_index = self.audio_device_combo.currentIndex()
        if 0 <= current_index < len(self.audio_devices):
            device_index = self.audio_devices[current_index]['index']
            self.config.set("audio.input_device_index", device_index)

        # 更新临时配置
        self.config.set("llm.base_url", self.llm_url.text())
        self.config.set("llm.model", self.model_name_input.text())

        # 同时更新 provider 永久配置
        mode = self.config.llm_mode
        self.config.update_provider_config(mode, "base_url", self.llm_url.text())

        # LM Studio 模式下从下拉框获取模型
        if mode == "lmstudio":
            model_index = self.model_combo.currentIndex()
            model_key = self.model_combo.itemData(model_index)
            if model_key:
                self.config.set("llm.model", model_key)
                self.config.update_provider_config(mode, "model", model_key)
            else:
                self.config.update_provider_config(mode, "model", self.model_name_input.text())
        else:
            # OpenAI/Ollama: 从输入框获取模型名称
            self.config.update_provider_config(mode, "model", self.model_name_input.text())

    def _update_ui_state(self):
        """更新 UI 状态"""
        # 如果模型正在加载，不更新按钮状态
        if self.is_model_loading:
            return

        if self.audio_capture.is_running():
            self.start_btn.setText("⏹ 卸载模型")
            self.start_btn.setStyleSheet("""
                QPushButton {
                    background-color: #F44336;
                    color: #FFFFFF;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 20px;
                    font-size: 15px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #E53935;
                }
            """)
            self.stt_model_combo.setEnabled(False)
            self.stt_device_combo.setEnabled(False)
            self.compute_type_combo.setEnabled(False)
            self.audio_device_combo.setEnabled(False)
            self.llm_combo.setEnabled(False)
        else:
            self.start_btn.setText("▶ 加载模型")
            self.start_btn.setStyleSheet("""
                QPushButton {
                    background-color: #0078D4;
                    color: #FFFFFF;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 20px;
                    font-size: 15px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #1084D8;
                }
            """)
            self.stt_model_combo.setEnabled(True)
            self.stt_device_combo.setEnabled(True)
            self.compute_type_combo.setEnabled(True)
            self.audio_device_combo.setEnabled(True)
            self.llm_combo.setEnabled(True)
            self.overlay.set_listen_button_enabled(False)
            self.status_label.setText("● 就绪（无模型）")
            self.status_label.setStyleSheet(f"color: {STATUS_COLORS['idle']};")
        self.start_btn.setEnabled(True)
        mode = self.config.llm_mode
        mode_names = {"openai": "OpenAI", "ollama": "Ollama", "lmstudio": "LM Studio"}
        self.status_label.setText(f"● 就绪 - {mode_names.get(mode, mode)}")
        self.status_label.setStyleSheet(f"color: {STATUS_COLORS['idle']};")
    
    def _on_transcription_ready(self, text: str):
        """转录文本就绪 - 显示在主窗口日志，发送问题给 LLM"""
        # 添加时间戳
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] 问题：{text}"
        self.transcription_log.append(log_entry)

        # 添加新问题到字幕窗口（开始新的一页），先显示问题，回答稍后流式显示
        self.overlay.caption_history.add_new_question(text)

        # 添加到队列并处理
        self.caption_queue.append(("question", text))
        self.status_label.setText("● 正在生成回答...")
        self.status_label.setStyleSheet(f"color: {STATUS_COLORS['generating']};")
        # 立即处理队列
        self._process_caption_queue()

    def _on_realtime_update(self, text: str):
        """实时转录更新 - 不更新字幕回答，只更新状态"""
        self.status_label.setText(f"● 听写中...")
        self.status_label.setStyleSheet(f"color: {STATUS_COLORS['listening']};")
        # 不再调用 update_caption，避免把转录文本误认为是回答
        # 实时转录已在主窗口日志中显示

    def _on_recording_started(self):
        """录音开始"""
        self._update_ui_state()
        self.status_label.setText("● 监听中...")
        self.status_label.setStyleSheet(f"color: {STATUS_COLORS['listening']};")
    
    def _on_model_loading_started(self):
        """模型开始加载 - 显示准备中状态"""
        self.is_model_loading = True
        self.start_btn.setText("⏳ 准备中...")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #9E9E9E;
                color: #BDBDBD;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 15px;
                font-weight: bold;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
                color: #757575;
            }
        """)
        self.start_btn.setEnabled(False)
        self.status_label.setText("● 模型加载中...")
        self.status_label.setStyleSheet("color: #9E9E9E;")
    
    def _on_model_loaded(self):
        """模型加载完成 - 更新为监听中状态"""
        self.is_model_loading = False
        log_system("模型加载完成", logging.INFO)
        self._update_ui_state()  # 恢复正常状态
        # 字幕窗口会在点击"开始监听"按钮，模型加载完成后显示
        self.overlay.show()
        self.caption_status.setText("字幕窗口：显示中（拖动顶部灰色条移动窗口，双击隐藏）")
        self.caption_toggle_btn.setText("📑 隐藏")
        # 启用 overlay 的监听按钮（模型已加载）
        if hasattr(self, "audio_capture") and self.audio_capture:
            self.overlay.set_listen_button_enabled(True)

    def _on_model_unloaded(self):
        """模型已卸载 - 更新 UI 状态"""
        log_system("模型已卸载", logging.INFO)
        self._update_ui_state()  # 更新 UI 状态

    def _on_recording_stopped(self):
        """录音停止"""
        self._update_ui_state()
    
    def _on_error(self, error_msg: str):
        """错误处理"""
        self.status_label.setText("● 错误")
        self.status_label.setStyleSheet(f"color: {STATUS_COLORS['error']};")
        QMessageBox.warning(self, "错误", error_msg)
    
    def _on_volume_update(self, volume: float):
        """音量更新"""
        self.current_volume = volume

    def _on_overlay_visibility_changed(self, visible: bool):
        """overlay 窗口可见性变化"""
        if visible:
            self.caption_status.setText("字幕窗口：显示中（拖动顶部灰色条移动窗口，双击隐藏）")
            self.caption_toggle_btn.setText("📑 隐藏")
        else:
            self.caption_status.setText("字幕窗口：已隐藏（点击字幕按钮或 F12 重新显示）")
            self.caption_toggle_btn.setText("📑 字幕")
    
    def _on_overlay_listening_started(self):
        """overlay 开始监听 - 启动手动录音"""
        # 检查模型是否是否已加载
        if self.is_model_loading or self.audio_capture.stt_model is None:
            QMessageBox.warning(self, "提示", "模型正在加载中，请稍后再试")
            log_system("录音失败：模型未加载", logging.WARNING)
            return

        # 先启动音频捕获（如果还没启动）
        if not self.audio_capture.is_running():
            self.audio_capture.start()
        # 设置为手动模式并开始录音
        self.audio_capture.set_manual_mode(True)
        if self.audio_capture._recording:
            return
        self.audio_capture._recording = True
        log_system(f"手动模式：开始录音 (时间: {time.strftime('%H:%M:%S')})", logging.INFO)

        self.status_label.setText("● 监听中（手动录音）...")
        self.status_label.setStyleSheet(f"color: {STATUS_COLORS['listening']};")

    def _on_overlay_listening_stopped(self):
        """overlay 停止监听 - 停止录音并转录"""
        # 停止录音（会自动触发转录）
        self.audio_capture.stop_recording()
        self.status_label.setText("● 已停止")
        self.status_label.setStyleSheet(f"color: {STATUS_COLORS['idle']};")

    def _update_volume_display(self):
        """更新音量显示"""
        volume_percent = int(self.current_volume * 100)
        volume_percent = min(100, volume_percent)
        
        self.volume_label.setText(f"音量：{volume_percent}%")
        
        if volume_percent < 10:
            color = "#4CAF50"
        elif volume_percent < 50:
            color = "#FFC107"
        else:
            color = "#F44336"
        
        self.volume_bar.setStyleSheet(f"""
            background-color: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 {color},
                stop:{volume_percent/100} {color},
                stop:{volume_percent/100} #2D2D2D,
                stop:1 #2D2D2D
            );
            border-radius: 4px;
        """)
    
    def _process_caption_queue(self):
        """处理字幕队列"""
        if not self.caption_queue:
            return

        item_type, text = self.caption_queue.pop(0)

        if item_type == "question":
            # 使用独立线程运行异步 LLM 调用（流式生成）
            threading.Thread(target=self._run_generate_answer_stream, args=(text,), daemon=True).start()

    def _run_generate_answer_stream(self, question: str):
        """在独立线程中运行异步 LLM 流式生成"""
        try:
            # 在新线程中运行异步函数
            asyncio.run(self._generate_and_show_answer_stream(question))
        except Exception as e:
            print(f"[DEBUG] _run_generate_answer_stream: error={e}", flush=True)
            import traceback
            traceback.print_exc()

    async def _generate_and_show_answer_stream(self, question: str):
        """流式生成并显示回答"""
        try:
            full_answer = ""
            current_page_index = self.overlay.caption_history.current_page
            print(f"[DEBUG] _generate_and_show_answer_stream: start, question='{question[:50]}...', current_page_index={current_page_index}", flush=True)

            def on_token(token: str):
                """每个 token 生成时的回调"""
                nonlocal full_answer
                full_answer += token
                # 发送信号到主线程更新UI
                self.token_signal.emit(token, current_page_index)

            full_answer = await self.llm_client.generate_answer_stream(question, self.resume_data, on_token)
            print(f"[DEBUG] _generate_and_show_answer_stream: done, answer len={len(full_answer)}", flush=True)
            log_llm(question, full_answer, self.config.llm_mode)
            # 发送完成信号
            self.complete_signal.emit(full_answer)
        except Exception as e:
            error_msg = f"生成失败：{str(e)}"
            log_system(error_msg, logging.ERROR)
            print(f"[DEBUG] _generate_and_show_answer_stream: error={e}", flush=True)
            self.error_signal.emit(error_msg)

    @pyqtSlot(str, int)
    def _on_token_update(self, token: str, page_index: int):
        """处理LLM token更新（在主线程中调用）"""
        print(f"[DEBUG] _on_token_update: token='{token[:20]}...', page_index={page_index}", flush=True)
        # 获取当前显示的文本并追加新token
        current_text = self.overlay.caption_history.pages[page_index]["answer"] if 0 <= page_index < len(self.overlay.caption_history.pages) else ""
        new_text = current_text + token
        self.overlay.caption_history.update_answer_streaming(new_text, page_index)

    @pyqtSlot(str)
    def _on_generation_complete(self, answer: str):
        """生成完成 - 更新状态"""
        self.status_label.setText("● 就绪")
        self.status_label.setStyleSheet(f"color: {STATUS_COLORS['idle']};")

    @pyqtSlot(str)
    def _on_llm_error_slot(self, error_msg: str):
        """LLM 错误处理（槽函数版本）"""
        log_system(error_msg, logging.ERROR)
        QMessageBox.warning(self, "生成失败", error_msg)
        self.status_label.setText("● 错误")
        self.status_label.setStyleSheet(f"color: {STATUS_COLORS['error']};")

        # 检测 503 错误，提示用户切换 LLM
        if "503" in error_msg or "Service Unavailable" in error_msg:
            QMessageBox.warning(self, "LLM 服务不可用", f"LM Studio 服务不可用 (503 错误)，请切换到其他 LLM 模式")

    def _on_llm_error(self, error_msg: str):
        """LLM 错误处理（主线程调用版本）"""
        log_system(error_msg, logging.ERROR)
        if self.overlay.isVisible():
            self.overlay.update_caption(f"错误：{error_msg}", "error")
        self.status_label.setText("● 错误")
        self.status_label.setStyleSheet(f"color: {STATUS_COLORS['error']};")

        # 检测 503 错误，提示用户切换 LLM
        if "503" in error_msg or "Service Unavailable" in error_msg:
            QMessageBox.warning(self, "LLM 服务不可用", f"LM Studio 服务不可用 (503 错误)，请切换到其他 LLM 模式")

    def _update_caption_streaming(self, current_text: str, page_index: int = None):
        """流式更新字幕 - 更新当前页的回答"""
        print(f"[DEBUG] _update_caption_streaming: current_text='{current_text[:50]}...' len={len(current_text)}, page_index={page_index}", flush=True)
        self.overlay.caption_history.update_answer_streaming(current_text, page_index)

    def _clear_transcription_log(self):
        """清空转录日志"""
        self.transcription_log.clear()

    def _open_log_folder(self):
        """打开日志文件夹"""
        import subprocess
        log_dir = os.path.join(os.getcwd(), 'logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            QMessageBox.information(self, "提示", "日志文件夹已创建，开始监听后会生成日志文件")
        try:
            subprocess.Popen(f'explorer "{log_dir}"')
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法打开日志文件夹：{e}")
    
    def _save_config(self):
        """保存配置到文件"""
        self._update_config_from_ui()
        try:
            self.config.save()
            QMessageBox.information(self, "保存成功", "配置已保存到 config.yaml")
            log_system("配置已保存", logging.INFO)
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"无法保存配置：{str(e)}")
            log_system(f"保存配置失败：{str(e)}", logging.ERROR)
    
    def closeEvent(self, event):
        """关闭窗口时的处理"""
        if self.audio_capture.is_running():
            self.audio_capture.stop()
        log_system("程序关闭，已停止音频捕获和音量监控", logging.INFO)
        event.accept()
