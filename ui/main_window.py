"""
主窗口 - 文档导入、配置、控制
"""

import asyncio
import datetime
import logging
import os
import re
import threading
import time
from typing import Any, Dict, List, Optional

import requests
import sounddevice as sd
from PySide6.QtCore import Qt, QTimer, Slot, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from core.logger import log_llm, log_system
from core.resume_parser import parse_resume
from ui.styles import (
    MAIN_WINDOW_STYLESHEET, STATUS_COLORS,
    BACKGROUND, SURFACE, TEXT_PRIMARY, TEXT_SECONDARY, BORDER_SUBTLE, ACCENT_PRIMARY,
    SECONDARY_BUTTON, DANGER_BUTTON, SUCCESS, ERROR
)
from ui.settings_dialog import AdvancedSettingsDialog


class MainWindow(QMainWindow):
    """主窗口"""

    # 信号用于线程间通信
    token_signal = Signal(str, int)  # token, page_index
    complete_signal = Signal(str)    # answer
    error_signal = Signal(str)       # error_msg

    def __init__(self, overlay_window, audio_capture, llm_client):
        super().__init__()
        self.overlay = overlay_window
        self.audio_capture = audio_capture
        self.llm_client = llm_client
        self.config = audio_capture.config
        
        self.resume_data: Optional[Dict[str, Any]] = None
        self.audio_devices: List[Dict] = []
        self.audio_output_devices: List[Dict] = []
        self.is_model_loading = False
        self._stt_download_canceled = False
        
        # Feature flag: 使用 Tab 布局（从配置读取，默认 True）
        self._use_new_layout = self.config.get("ui.use_tab_layout", True)
        
        self._init_ui()
        print("[Debug] _init_ui 完成", flush=True)
        self._connect_signals()
        print("[Debug] _connect_signals 完成", flush=True)
        self._load_audio_devices()
        print("[Debug] _load_audio_devices 完成", flush=True)
        self._sync_ui_with_config()
        print("[Debug] _sync_ui_with_config 完成", flush=True)
        self._load_saved_document()  # 自动加载保存的文档
        print("[Debug] _load_saved_document 完成", flush=True)

        # 启动音量监控（独立于录音）
        self.audio_capture.start_monitoring()
        self._initialized = True
        print("[Debug] MainWindow 初始化完成", flush=True)
    
    def _on_audio_device_changed(self, index):
        """音频设备切换 - 区分输入设备和输出设备"""
        if index < 0:
            return

        is_output = self.speaker_radio.isChecked()
        devices = self.audio_output_devices if is_output else self.audio_devices

        if index >= len(devices):
            return

        device = devices[index]
        device_index = device['index']

        # 更新配置 - 根据设备类型保存到不同的配置项
        if is_output:
            self.config.set("audio.output_device_index", device_index)
            print(f"[Debug] 切换到输出设备：{device['name']} (索引：{device_index})", flush=True)
        else:
            self.config.set("audio.input_device_index", device_index)
            print(f"[Debug] 切换到输入设备：{device['name']} (索引：{device_index})", flush=True)

        # 重启音量监控以使用新设备
        self.audio_capture.restart_monitoring()
    
    def _init_ui(self):
        """初始化 UI - 根据 feature flag 选择布局"""
        
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
        
        # 根据 feature flag 选择布局
        if self._use_new_layout:
            self._init_ui_tabs(central_widget)
        else:
            self._init_ui_classic(central_widget)
        
        self._update_ui_state()
    
    def _init_ui_classic(self, central_widget: QWidget):
        """经典布局 - 使用 QGroupBox 分组"""
        
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # 状态标签
        self.status_label = QLabel("● 就绪")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # 文档导入
        resume_group = QGroupBox("知识库文档（可选）")
        resume_layout = QVBoxLayout(resume_group)
        
        # 路径显示/编辑行
        path_row = QHBoxLayout()
        
        # 状态指示器（文件存在显示绿色checkmark，不存在显示红色warning）
        self.doc_status_btn = QToolButton()
        self.doc_status_btn.setFixedSize(24, 24)
        self.doc_status_btn.setStyleSheet("QToolButton { border: none; background: transparent; }")
        self.doc_status_btn.setToolTip("文档状态")
        self.doc_status_btn.setVisible(False)
        path_row.addWidget(self.doc_status_btn)
        
        # 路径输入框
        self.resume_path_input = QLineEdit()
        self.resume_path_input.setPlaceholderText("输入 Markdown 文件路径，或点击浏览...")
        self.resume_path_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {SURFACE};
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER_SUBTLE};
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 12px;
            }}
            QLineEdit:focus {{
                border: 1px solid {ACCENT_PRIMARY};
            }}
        """)
        self.resume_path_input.returnPressed.connect(self._on_resume_path_entered)
        path_row.addWidget(self.resume_path_input, stretch=1)
        
        # 浏览按钮
        browse_btn = QPushButton("浏览...")
        browse_btn.setStyleSheet(SECONDARY_BUTTON)
        browse_btn.clicked.connect(self._select_resume)
        path_row.addWidget(browse_btn)
        
        # 清空按钮
        clear_btn = QPushButton("清空")
        clear_btn.setStyleSheet(DANGER_BUTTON)
        clear_btn.clicked.connect(self._clear_resume)
        clear_btn.setToolTip("清除文档路径和内容")
        path_row.addWidget(clear_btn)
        
        resume_layout.addLayout(path_row)
        
        # 文档摘要显示（可选）
        self.resume_summary_label = QLabel("")
        self.resume_summary_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; padding: 4px;")
        resume_layout.addWidget(self.resume_summary_label)
        
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
        self.llm_url.setPlaceholderText("http://127.0.0.1")

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

        # 设备类型选择（麦克风/扬声器）
        device_type_layout = QHBoxLayout()
        self.device_type_group = QButtonGroup(self)
        self.mic_radio = QRadioButton("麦克风")
        self.speaker_radio = QRadioButton("扬声器/耳机")
        self.speaker_radio.setChecked(True)  # 默认优先监听会议声音输出
        self.device_type_group.addButton(self.mic_radio, 0)
        self.device_type_group.addButton(self.speaker_radio, 1)
        # 使用 QButtonGroup 的信号，捕获两个 radio button 的状态变化
        self.device_type_group.idToggled.connect(self._on_device_type_changed)
        device_type_layout.addWidget(self.mic_radio)
        device_type_layout.addWidget(self.speaker_radio)
        device_type_layout.addStretch()
        audio_form.addRow("监听源:", device_type_layout)

        # 音频设备选择行（包含下拉框和刷新按钮）
        device_select_layout = QHBoxLayout()
        self.audio_device_combo = QComboBox()
        self.audio_device_combo.setSizePolicy(
            self.audio_device_combo.sizePolicy().horizontalPolicy(),
            self.audio_device_combo.sizePolicy().verticalPolicy()
        )
        self.refresh_devices_btn = QPushButton("刷新")
        self.refresh_devices_btn.setFixedWidth(60)
        self.refresh_devices_btn.setFixedHeight(28)
        self.refresh_devices_btn.clicked.connect(self._refresh_audio_devices)
        device_select_layout.addWidget(self.audio_device_combo)
        device_select_layout.addWidget(self.refresh_devices_btn)
        audio_form.addRow("设备:", device_select_layout)

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
        
        # 高级设置按钮
        self.advanced_btn = QPushButton("⚙ 高级设置")
        self.advanced_btn.setMinimumHeight(45)
        self.advanced_btn.setStyleSheet(SECONDARY_BUTTON)
        self.advanced_btn.setToolTip("打开高级配置对话框")
        self.advanced_btn.clicked.connect(self._open_advanced_settings)
        button_layout.addWidget(self.advanced_btn)
        
        # 查看日志按钮
        self.view_log_btn = QPushButton("📋 查看日志")
        self.view_log_btn.setMinimumHeight(45)
        self.view_log_btn.setStyleSheet(SECONDARY_BUTTON)
        self.view_log_btn.setToolTip("查看转录日志")
        self.view_log_btn.clicked.connect(self._open_transcription_log)
        button_layout.addWidget(self.view_log_btn)
        
        layout.addLayout(button_layout)

        # 字幕状态
        self.caption_status = QLabel("字幕窗口：未显示（点击后显示/隐藏，拖动顶部灰色条移动窗口）")
        self.caption_status.setStyleSheet("color: #9AA0A6; font-size: 11px;")
        layout.addWidget(self.caption_status)
        
        # 转录日志数据（内部存储，不直接显示）
        self.transcription_log_data = []  # 存储日志条目
    
    def _init_ui_tabs(self, central_widget: QWidget):
        """Tab 布局 - 使用 QTabWidget 分组"""
        
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # 状态标签（始终显示在顶部）
        self.status_label = QLabel("● 就绪")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # 创建 Tab Widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName("mainTabWidget")
        layout.addWidget(self.tab_widget, stretch=1)
        
        # 创建各个 Tab
        self.tab_widget.addTab(self._create_main_tab(), "主面板")
        self.tab_widget.addTab(self._create_llm_tab(), "LLM 设置")
        self.tab_widget.addTab(self._create_stt_tab(), "STT 设置")
        self.tab_widget.addTab(self._create_display_tab(), "显示设置")
        self.tab_widget.addTab(self._create_log_tab(), "日志")
        
        # 字幕状态（始终显示在底部）
        self.caption_status = QLabel("字幕窗口：未显示（点击后显示/隐藏，拖动顶部灰色条移动窗口）")
        self.caption_status.setStyleSheet("color: #9AA0A6; font-size: 11px;")
        layout.addWidget(self.caption_status)
        
        # 转录日志数据（内部存储，不直接显示）
        self.transcription_log_data = []
    
    def _create_main_tab(self) -> QWidget:
        """创建主面板 Tab - 状态显示、文档路径、控制按钮"""
        
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # 文档导入
        resume_group = QGroupBox("知识库文档（可选）")
        resume_layout = QVBoxLayout(resume_group)
        
        # 路径显示/编辑行
        path_row = QHBoxLayout()
        
        # 状态指示器
        self.doc_status_btn = QToolButton()
        self.doc_status_btn.setFixedSize(24, 24)
        self.doc_status_btn.setStyleSheet("QToolButton { border: none; background: transparent; }")
        self.doc_status_btn.setToolTip("文档状态")
        self.doc_status_btn.setVisible(False)
        path_row.addWidget(self.doc_status_btn)
        
        # 路径输入框
        self.resume_path_input = QLineEdit()
        self.resume_path_input.setPlaceholderText("输入 Markdown 文件路径，或点击浏览...")
        self.resume_path_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {SURFACE};
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER_SUBTLE};
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 12px;
            }}
            QLineEdit:focus {{
                border: 1px solid {ACCENT_PRIMARY};
            }}
        """)
        self.resume_path_input.returnPressed.connect(self._on_resume_path_entered)
        path_row.addWidget(self.resume_path_input, stretch=1)
        
        # 浏览按钮
        browse_btn = QPushButton("浏览...")
        browse_btn.setStyleSheet(SECONDARY_BUTTON)
        browse_btn.clicked.connect(self._select_resume)
        path_row.addWidget(browse_btn)
        
        # 清空按钮
        clear_btn = QPushButton("清空")
        clear_btn.setStyleSheet(DANGER_BUTTON)
        clear_btn.clicked.connect(self._clear_resume)
        clear_btn.setToolTip("清除文档路径和内容")
        path_row.addWidget(clear_btn)
        
        resume_layout.addLayout(path_row)
        
        # 文档摘要显示
        self.resume_summary_label = QLabel("")
        self.resume_summary_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; padding: 4px;")
        resume_layout.addWidget(self.resume_summary_label)
        
        layout.addWidget(resume_group)
        
        # 音频设置（简化版）
        audio_group = QGroupBox("音频设置")
        audio_layout = QVBoxLayout(audio_group)
        
        audio_form = QFormLayout()
        
        # 设备类型选择
        device_type_layout = QHBoxLayout()
        self.device_type_group = QButtonGroup(self)
        self.mic_radio = QRadioButton("麦克风")
        self.speaker_radio = QRadioButton("扬声器/耳机")
        self.speaker_radio.setChecked(True)
        self.device_type_group.addButton(self.mic_radio, 0)
        self.device_type_group.addButton(self.speaker_radio, 1)
        self.device_type_group.idToggled.connect(self._on_device_type_changed)
        device_type_layout.addWidget(self.mic_radio)
        device_type_layout.addWidget(self.speaker_radio)
        device_type_layout.addStretch()
        audio_form.addRow("监听源:", device_type_layout)
        
        # 音频设备选择
        device_select_layout = QHBoxLayout()
        self.audio_device_combo = QComboBox()
        self.refresh_devices_btn = QPushButton("刷新")
        self.refresh_devices_btn.setFixedWidth(60)
        self.refresh_devices_btn.setFixedHeight(28)
        self.refresh_devices_btn.clicked.connect(self._refresh_audio_devices)
        device_select_layout.addWidget(self.audio_device_combo)
        device_select_layout.addWidget(self.refresh_devices_btn)
        audio_form.addRow("设备:", device_select_layout)
        
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
        
        # 控制按钮
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
        
        self.caption_toggle_btn = QPushButton("📑 字幕")
        self.caption_toggle_btn.setMinimumHeight(45)
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
        
        self.advanced_btn = QPushButton("⚙ 高级设置")
        self.advanced_btn.setMinimumHeight(45)
        self.advanced_btn.setStyleSheet(SECONDARY_BUTTON)
        self.advanced_btn.setToolTip("打开高级配置对话框")
        self.advanced_btn.clicked.connect(self._open_advanced_settings)
        button_layout.addWidget(self.advanced_btn)
        
        self.view_log_btn = QPushButton("📋 查看日志")
        self.view_log_btn.setMinimumHeight(45)
        self.view_log_btn.setStyleSheet(SECONDARY_BUTTON)
        self.view_log_btn.setToolTip("查看转录日志")
        self.view_log_btn.clicked.connect(self._open_transcription_log)
        button_layout.addWidget(self.view_log_btn)
        
        layout.addLayout(button_layout)
        layout.addStretch()
        
        return tab
    
    def _create_llm_tab(self) -> QWidget:
        """创建 LLM 设置 Tab - 包含基础设置和高级设置"""
        
        # 使用 QScrollArea 包装内容
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet(f"QScrollArea {{ border: none; background-color: {BACKGROUND}; }}")
        
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # 基础设置
        llm_group = QGroupBox("大模型设置")
        llm_group.setStyleSheet(f"""
            QGroupBox {{
                color: {TEXT_PRIMARY};
                font-weight: 500;
                border: 1px solid {BORDER_SUBTLE};
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 8px;
            }}
            QGroupBox::title {{
                color: {TEXT_SECONDARY};
                padding: 0 8px;
            }}
        """)
        llm_layout = QVBoxLayout(llm_group)
        
        llm_form = QFormLayout()
        
        # Provider 选择
        self.llm_combo = QComboBox()
        self.llm_combo.addItems(["OpenAI (云端)", "Ollama（本地）", "LM Studio (本地)"])
        self.llm_combo.currentIndexChanged.connect(self._on_llm_changed)
        llm_form.addRow("模型模式:", self.llm_combo)
        
        # 模型名称输入框
        self.model_name_input = QLineEdit()
        self.model_name_input.setPlaceholderText("如：qwen3.5-plus, qwen2.5:7b")
        self.model_name_input_label = QLabel("模型名称:")
        llm_form.addRow(self.model_name_input_label, self.model_name_input)
        
        # Base URL 输入框
        self.llm_url = QLineEdit()
        self.llm_url.setPlaceholderText("http://127.0.0.1")
        llm_form.addRow("Base URL:", self.llm_url)
        
        # LM Studio 模型刷新按钮和下拉框
        self.refresh_models_btn = QPushButton("🔄 刷新模型列表")
        self.refresh_models_btn.setToolTip("从 LM Studio 获取可用模型")
        self.refresh_models_btn.setFixedHeight(28)
        self.refresh_models_btn.clicked.connect(self._refresh_lmstudio_models)
        self.refresh_models_btn.setEnabled(False)
        
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.setToolTip("从 LM Studio 选择模型（鼠标悬停查看参数）")
        self.model_combo.setEnabled(False)
        self.model_combo.currentIndexChanged.connect(self._on_model_combo_changed)
        
        self.model_combo_layout = QHBoxLayout()
        self.model_combo_layout.setSpacing(4)
        self.model_combo_layout.addWidget(self.model_combo)
        self.model_combo_layout.addWidget(self.refresh_models_btn)
        self.model_combo_label = QLabel("选择模型:")
        llm_form.addRow(self.model_combo_label, self.model_combo_layout)
        
        llm_layout.addLayout(llm_form)
        layout.addWidget(llm_group)
        
        # 生成参数（高级设置）
        gen_group = QGroupBox("生成参数")
        gen_group.setStyleSheet(llm_group.styleSheet())
        gen_form = QFormLayout(gen_group)
        
        self.temp_spin = QDoubleSpinBox()
        self.temp_spin.setRange(0.0, 2.0)
        self.temp_spin.setSingleStep(0.1)
        self.temp_spin.setDecimals(1)
        self.temp_spin.setToolTip("温度越高，回答越随机；越低越确定")
        gen_form.addRow("温度 (temperature):", self.temp_spin)
        
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(100, 4000)
        self.max_tokens_spin.setToolTip("单次生成的最大 token 数")
        gen_form.addRow("最大 Token (非流式):", self.max_tokens_spin)
        
        self.max_tokens_stream_spin = QSpinBox()
        self.max_tokens_stream_spin.setRange(100, 4000)
        self.max_tokens_stream_spin.setToolTip("流式生成的最大 token 数")
        gen_form.addRow("最大 Token (流式):", self.max_tokens_stream_spin)
        
        self.reasoning_combo = QComboBox()
        self.reasoning_combo.addItems(["none", "minimal", "low", "medium", "high", "xhigh"])
        self.reasoning_combo.setToolTip("Qwen 模型的推理努力程度")
        gen_form.addRow("推理努力:", self.reasoning_combo)
        
        layout.addWidget(gen_group)
        
        # 提示词模板（高级设置）
        prompt_group = QGroupBox("提示词模板")
        prompt_group.setStyleSheet(llm_group.styleSheet())
        prompt_form = QFormLayout(prompt_group)
        
        self.prompt_base_input = QLineEdit()
        self.prompt_base_input.setToolTip("系统提示词基础")
        prompt_form.addRow("基础提示词:", self.prompt_base_input)
        
        self.prompt_words_input = QLineEdit()
        self.prompt_words_input.setToolTip("期望回答字数范围")
        prompt_form.addRow("字数范围:", self.prompt_words_input)
        
        self.prompt_theme_input = QLineEdit()
        self.prompt_theme_input.setToolTip("面试主题")
        prompt_form.addRow("主题:", self.prompt_theme_input)
        
        layout.addWidget(prompt_group)
        
        # 保存按钮
        save_btn = QPushButton("💾 保存配置")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078D4;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #1084D8;
            }
        """)
        save_btn.clicked.connect(self._save_config)
        layout.addWidget(save_btn)
        
        layout.addStretch()
        
        scroll_area.setWidget(tab)
        return scroll_area
    
    def _create_stt_tab(self) -> QWidget:
        """创建 STT 设置 Tab - 包含基础设置和高级设置"""
        
        # 使用 QScrollArea 包装内容
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet(f"QScrollArea {{ border: none; background-color: {BACKGROUND}; }}")
        
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # 基础设置
        stt_group = QGroupBox("语音识别 (STT) 设置")
        stt_group.setStyleSheet(f"""
            QGroupBox {{
                color: {TEXT_PRIMARY};
                font-weight: 500;
                border: 1px solid {BORDER_SUBTLE};
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 8px;
            }}
            QGroupBox::title {{
                color: {TEXT_SECONDARY};
                padding: 0 8px;
            }}
        """)
        stt_layout = QVBoxLayout(stt_group)
        
        stt_form = QFormLayout()
        
        # STT 模型选择
        self.stt_model_combo = QComboBox()
        self.stt_model_combo.addItems([
            "tiny (75MB, 最快)",
            "base (143MB, 快)",
            "small (467MB, 平衡)",
            "medium (1.5GB, 推荐)",
            "large-v2 (2.9GB, 最准确)",
            "large-v3 (3GB, 最新)"
        ])
        self.stt_model_combo.setCurrentIndex(3)
        stt_form.addRow("模型:", self.stt_model_combo)
        
        # 计算设备选择
        self.stt_device_combo = QComboBox()
        self.stt_device_combo.addItems(["CPU", "CUDA (GPU)"])
        self.stt_device_combo.setCurrentIndex(1)
        stt_form.addRow("计算设备:", self.stt_device_combo)
        
        # 计算类型选择
        self.compute_type_combo = QComboBox()
        self.compute_type_combo.addItems(["float32 (兼容)", "float16 (快速)", "int8 (省显存)"])
        self.compute_type_combo.setCurrentIndex(0)
        stt_form.addRow("计算类型:", self.compute_type_combo)
        
        stt_layout.addLayout(stt_form)
        layout.addWidget(stt_group)
        
        # 自动分句参数（高级设置）
        auto_group = QGroupBox("自动分句参数（仅自动模式生效）")
        auto_group.setStyleSheet(stt_group.styleSheet())
        auto_form = QFormLayout(auto_group)
        
        self.volume_threshold_spin = QDoubleSpinBox()
        self.volume_threshold_spin.setRange(0.001, 0.1)
        self.volume_threshold_spin.setSingleStep(0.001)
        self.volume_threshold_spin.setDecimals(3)
        self.volume_threshold_spin.setToolTip("RMS 音量阈值，越大越不敏感")
        auto_form.addRow("音量阈值:", self.volume_threshold_spin)
        
        self.voice_ratio_spin = QDoubleSpinBox()
        self.voice_ratio_spin.setRange(1.0, 10.0)
        self.voice_ratio_spin.setSingleStep(0.1)
        self.voice_ratio_spin.setToolTip("起始语音阈值倍数")
        auto_form.addRow("语音倍数:", self.voice_ratio_spin)
        
        self.silence_ratio_spin = QDoubleSpinBox()
        self.silence_ratio_spin.setRange(1.0, 10.0)
        self.silence_ratio_spin.setSingleStep(0.1)
        self.silence_ratio_spin.setToolTip("语音保持阈值倍数")
        auto_form.addRow("静音倍数:", self.silence_ratio_spin)
        
        self.noise_alpha_spin = QDoubleSpinBox()
        self.noise_alpha_spin.setRange(0.01, 0.5)
        self.noise_alpha_spin.setSingleStep(0.01)
        self.noise_alpha_spin.setDecimals(2)
        self.noise_alpha_spin.setToolTip("噪声底 EMA 更新系数")
        auto_form.addRow("噪声系数:", self.noise_alpha_spin)
        
        self.pause_seconds_spin = QDoubleSpinBox()
        self.pause_seconds_spin.setRange(0.2, 3.0)
        self.pause_seconds_spin.setSingleStep(0.1)
        self.pause_seconds_spin.setToolTip("静音多久判定句子结束")
        auto_form.addRow("静音时长 (秒):", self.pause_seconds_spin)
        
        self.min_sentence_spin = QDoubleSpinBox()
        self.min_sentence_spin.setRange(1.0, 5.0)
        self.min_sentence_spin.setSingleStep(0.5)
        self.min_sentence_spin.setToolTip("最短句长，太短不触发")
        auto_form.addRow("最短句 (秒):", self.min_sentence_spin)
        
        self.max_sentence_spin = QDoubleSpinBox()
        self.max_sentence_spin.setRange(5.0, 30.0)
        self.max_sentence_spin.setSingleStep(1.0)
        self.max_sentence_spin.setToolTip("最长句长，超时强制切分")
        auto_form.addRow("最长句 (秒):", self.max_sentence_spin)
        
        self.resume_chunks_spin = QSpinBox()
        self.resume_chunks_spin.setRange(1, 10)
        self.resume_chunks_spin.setToolTip("从静音恢复需要的有声块数")
        auto_form.addRow("恢复块数:", self.resume_chunks_spin)
        
        layout.addWidget(auto_group)
        
        # 下载与语言（高级设置）
        download_group = QGroupBox("下载与语言")
        download_group.setStyleSheet(stt_group.styleSheet())
        download_form = QFormLayout(download_group)
        
        self.download_mirror_input = QLineEdit()
        self.download_mirror_input.setToolTip("HuggingFace 镜像地址")
        download_form.addRow("下载镜像:", self.download_mirror_input)
        
        self.cache_dir_input = QLineEdit()
        self.cache_dir_input.setToolTip("模型缓存目录，留空使用默认")
        download_form.addRow("缓存目录:", self.cache_dir_input)
        
        self.stt_language_combo = QComboBox()
        self.stt_language_combo.addItems(["zh", "en", "ja", "auto"])
        self.stt_language_combo.setToolTip("转录语言")
        download_form.addRow("转录语言:", self.stt_language_combo)
        
        self.stt_hotwords_input = QLineEdit()
        self.stt_hotwords_input.setToolTip("热词列表，空格分隔")
        download_form.addRow("热词:", self.stt_hotwords_input)
        
        self.stt_model_path_input = QLineEdit()
        self.stt_model_path_input.setToolTip("本地模型路径，留空自动下载")
        download_form.addRow("本地模型路径:", self.stt_model_path_input)
        
        layout.addWidget(download_group)
        
        # 保存按钮
        save_btn = QPushButton("💾 保存配置")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078D4;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #1084D8;
            }
        """)
        save_btn.clicked.connect(self._save_config)
        layout.addWidget(save_btn)
        
        layout.addStretch()
        
        scroll_area.setWidget(tab)
        return scroll_area
    
    def _create_display_tab(self) -> QWidget:
        """创建显示设置 Tab - Overlay 高度/宽度比例、字体大小、热键配置"""
        
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Overlay 设置
        overlay_group = QGroupBox("字幕窗口设置")
        overlay_layout = QVBoxLayout(overlay_group)
        
        overlay_form = QFormLayout()
        
        # 高度比例（从配置读取）
        height_ratio = self.config.get("overlay.height_ratio", 0.15)
        self.height_ratio_label = QLabel(f"{height_ratio:.2f}")
        overlay_form.addRow("高度比例:", self.height_ratio_label)
        
        # 宽度比例（从配置读取）
        width_ratio = self.config.get("overlay.width_ratio", 0.8)
        self.width_ratio_label = QLabel(f"{width_ratio:.2f}")
        overlay_form.addRow("宽度比例:", self.width_ratio_label)
        
        # 字体大小（从配置读取）
        font_size = self.config.get("overlay.font_size", 18)
        self.font_size_label = QLabel(f"{font_size} px")
        overlay_form.addRow("字体大小:", self.font_size_label)
        
        overlay_layout.addLayout(overlay_form)
        layout.addWidget(overlay_group)
        
        # 热键配置
        hotkey_group = QGroupBox("快捷键配置")
        hotkey_layout = QVBoxLayout(hotkey_group)
        
        hotkey_form = QFormLayout()
        
        # 显示/隐藏字幕窗口
        overlay_key = self.config.get("hotkeys.overlay_visibility", "Ctrl+F4")
        hotkey_form.addRow("显示/隐藏字幕:", QLabel(overlay_key))
        
        # 切换自动/手动模式
        mode_key = self.config.get("hotkeys.transcription_mode", "Ctrl+F6")
        hotkey_form.addRow("切换转录模式:", QLabel(mode_key))
        
        # 开始/结束监听
        listen_key = self.config.get("hotkeys.listening_toggled", "Ctrl+F8")
        hotkey_form.addRow("开始/结束监听:", QLabel(listen_key))
        
        # 上一条字幕
        prev_key = self.config.get("hotkeys.prev_caption", "Ctrl+F7")
        hotkey_form.addRow("上一条字幕:", QLabel(prev_key))
        
        # 下一条字幕
        next_key = self.config.get("hotkeys.next_caption", "Ctrl+F9")
        hotkey_form.addRow("下一条字幕:", QLabel(next_key))
        
        hotkey_layout.addLayout(hotkey_form)
        layout.addWidget(hotkey_group)
        
        # 提示信息
        hint_label = QLabel("提示：以上设置可在 config.yaml 或高级设置中修改")
        hint_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
        layout.addWidget(hint_label)
        
        layout.addStretch()
        
        return tab
    
    def _create_log_tab(self) -> QWidget:
        """创建日志 Tab - 显示转录日志和系统日志"""
        
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # 转录日志
        transcription_group = QGroupBox("转录日志")
        transcription_group.setStyleSheet(f"""
            QGroupBox {{
                color: {TEXT_PRIMARY};
                font-weight: 500;
                border: 1px solid {BORDER_SUBTLE};
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 8px;
            }}
            QGroupBox::title {{
                color: {TEXT_SECONDARY};
                padding: 0 8px;
            }}
        """)
        transcription_layout = QVBoxLayout(transcription_group)
        
        # 转录日志文本框
        self.transcription_log_text = QTextEdit()
        self.transcription_log_text.setReadOnly(True)
        self.transcription_log_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {BACKGROUND};
                color: {TEXT_SECONDARY};
                border: 1px solid {BORDER_SUBTLE};
                border-radius: 4px;
                padding: 8px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
            }}
        """)
        self.transcription_log_text.setPlaceholderText("暂无转录日志...")
        transcription_layout.addWidget(self.transcription_log_text)
        
        # 转录日志按钮
        transcription_btn_layout = QHBoxLayout()
        
        clear_transcription_btn = QPushButton("清空转录日志")
        clear_transcription_btn.setStyleSheet(DANGER_BUTTON)
        clear_transcription_btn.clicked.connect(self._clear_transcription_log)
        transcription_btn_layout.addWidget(clear_transcription_btn)
        
        transcription_btn_layout.addStretch()
        transcription_layout.addLayout(transcription_btn_layout)
        
        layout.addWidget(transcription_group)
        
        # 系统日志
        system_group = QGroupBox("系统日志")
        system_group.setStyleSheet(transcription_group.styleSheet())
        system_layout = QVBoxLayout(system_group)
        
        # 系统日志文本框
        self.system_log_text = QTextEdit()
        self.system_log_text.setReadOnly(True)
        self.system_log_text.setStyleSheet(self.transcription_log_text.styleSheet())
        self.system_log_text.setPlaceholderText("暂无系统日志...")
        system_layout.addWidget(self.system_log_text)
        
        # 系统日志按钮
        system_btn_layout = QHBoxLayout()
        
        refresh_log_btn = QPushButton("刷新日志")
        refresh_log_btn.setStyleSheet(SECONDARY_BUTTON)
        refresh_log_btn.clicked.connect(self._refresh_system_log)
        system_btn_layout.addWidget(refresh_log_btn)
        
        open_log_btn = QPushButton("打开日志文件夹")
        open_log_btn.setStyleSheet(SECONDARY_BUTTON)
        open_log_btn.clicked.connect(self._open_log_folder)
        system_btn_layout.addWidget(open_log_btn)
        
        system_btn_layout.addStretch()
        system_layout.addLayout(system_btn_layout)
        
        layout.addWidget(system_group)
        
        # 启动定时器刷新日志
        self.log_refresh_timer = QTimer()
        self.log_refresh_timer.timeout.connect(self._refresh_logs_display)
        self.log_refresh_timer.start(2000)  # 每 2 秒刷新
        
        layout.addStretch()
        
        return tab
    
    def _refresh_logs_display(self):
        """刷新日志显示"""
        # 刷新转录日志
        if hasattr(self, 'transcription_log_text') and self.transcription_log_text:
            if self.transcription_log_data:
                self.transcription_log_text.setText("\n".join(self.transcription_log_data))
            else:
                self.transcription_log_text.clear()
        
        # 刷新系统日志
        self._refresh_system_log()
    
    def _refresh_system_log(self):
        """刷新系统日志显示"""
        if not hasattr(self, 'system_log_text') or not self.system_log_text:
            return
        
        try:
            log_dir = os.path.join(os.getcwd(), 'logs')
            system_log_path = os.path.join(log_dir, 'system.log')
            
            if os.path.exists(system_log_path):
                with open(system_log_path, 'r', encoding='utf-8') as f:
                    # 只读取最后 100 行
                    lines = f.readlines()
                    last_lines = lines[-100:] if len(lines) > 100 else lines
                    self.system_log_text.setText("".join(last_lines))
            else:
                self.system_log_text.setPlaceholderText("日志文件尚未生成...")
        except Exception as e:
            self.system_log_text.setText(f"读取日志失败: {str(e)}")
    
    def _load_audio_devices(self):
        """加载音频设备列表 - 支持输入设备和输出设备"""
        try:
            devices = sd.query_devices()
            self.audio_devices = []
            self.audio_output_devices = []

            # 分离输入设备和输出设备
            for i, dev in enumerate(devices):
                # 输入设备（麦克风）
                if dev['max_input_channels'] > 0:
                    device_name = f"{i}: {dev['name'][:40]} (输入:{dev['max_input_channels']})"
                    self.audio_devices.append({
                        'index': i,
                        'name': dev['name'],
                        'channels': dev['max_input_channels'],
                        'type': 'input'
                    })
                # 输出设备（扬声器/耳机）- 用于 loopback 监听
                if dev['max_output_channels'] > 0:
                    device_name = f"{i}: {dev['name'][:40]} (输出:{dev['max_output_channels']})"
                    self.audio_output_devices.append({
                        'index': i,
                        'name': dev['name'],
                        'channels': dev['max_output_channels'],
                        'type': 'output'
                    })

            print(f"[Debug] 加载了 {len(self.audio_devices)} 个输入设备, {len(self.audio_output_devices)} 个输出设备", flush=True)

            # 根据当前设备类型更新下拉框
            self._update_device_combo()

        except Exception as e:
            print(f"[Error] 加载音频设备失败：{e}", flush=True)
            self.audio_devices = [{'index': 0, 'name': '默认设备', 'channels': 2, 'type': 'input'}]
            self.audio_output_devices = [{'index': 0, 'name': '默认设备', 'channels': 2, 'type': 'output'}]
            self._update_device_combo()

    def _update_device_combo(self):
        """根据设备类型更新下拉框显示"""
        # 阻止信号触发
        self.audio_device_combo.blockSignals(True)
        self.audio_device_combo.clear()

        # 根据当前选中的设备类型决定显示哪些设备
        is_output = self.speaker_radio.isChecked()
        devices = self.audio_output_devices if is_output else self.audio_devices

        for dev in devices:
            device_name = f"{dev['index']}: {dev['name'][:35]} ({'输出' if is_output else '输入'}:{dev['channels']})"
            self.audio_device_combo.addItem(device_name)

        # 从配置恢复选择的设备
        if is_output:
            configured_index = self.config.get("audio.output_device_index", None)
        else:
            configured_index = self.config.get("audio.input_device_index", None)

        found_configured = False
        if configured_index is not None:
            for i, dev in enumerate(devices):
                if dev['index'] == configured_index:
                    self.audio_device_combo.setCurrentIndex(i)
                    found_configured = True
                    break

        # 如果配置中没有设备索引，保存第一个设备作为默认值
        if not found_configured and len(devices) > 0:
            first_device = devices[0]
            if is_output:
                self.config.set("audio.output_device_index", first_device['index'])
            else:
                self.config.set("audio.input_device_index", first_device['index'])
            print(f"[Debug] 自动保存默认设备：{first_device['name']} (索引：{first_device['index']})", flush=True)

        self.audio_device_combo.blockSignals(False)

        # 连接设备切换信号
        try:
            self.audio_device_combo.currentIndexChanged.disconnect()
        except TypeError:
            pass  # 信号未连接
        self.audio_device_combo.currentIndexChanged.connect(self._on_audio_device_changed)

    def _on_device_type_changed(self, button_id, checked):
        """设备类型切换（麦克风/扬声器）- QButtonGroup.idToggled 信号"""
        # 只处理 checked=True 的信号（选中事件）
        if not checked:
            return

        # button_id: 0 = mic_radio, 1 = speaker_radio
        is_output = (button_id == 1)  # speaker_radio 的 ID 是 1
        print(f"[Debug] 切换设备类型: {'扬声器' if is_output else '麦克风'} (button_id={button_id})", flush=True)

        # 更新配置
        self.config.set("audio.use_microphone", not is_output)

        # 更新设备下拉框
        self._update_device_combo()

        # 重启音量监控以使用新设备类型
        if hasattr(self, 'audio_capture') and self.audio_capture:
            self.audio_capture.restart_monitoring()

    def _refresh_audio_devices(self):
        """刷新音频设备列表"""
        print("[Debug] 刷新音频设备列表", flush=True)
        self.refresh_devices_btn.setText("...")
        self.refresh_devices_btn.setEnabled(False)

        try:
            self._load_audio_devices()
        finally:
            self.refresh_devices_btn.setText("刷新")
            self.refresh_devices_btn.setEnabled(True)
    
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
        
        # 初始化时自动刷新 LM Studio 模型列表
        if is_lmstudio:
            print("[Debug] _sync_ui_with_config: 自动刷新 LM Studio 模型列表", flush=True)
            self._refresh_lmstudio_models()

        model_map = {"tiny": 0, "base": 1, "small": 2, "medium": 3, "large-v2": 4, "large-v3": 5}
        self.stt_model_combo.setCurrentIndex(model_map.get(self.config.stt_model, 3))

        # 同步 STT 设备选择
        device_map = {"cpu": 0, "cuda": 1, "gpu": 1}
        stt_device = self.config.get("stt.local.device", "cuda").lower()
        self.stt_device_combo.setCurrentIndex(device_map.get(stt_device, 1))

        compute_map = {"float32": 0, "float16": 1, "int8": 2}
        self.compute_type_combo.setCurrentIndex(compute_map.get(self.config.get("stt.local.compute_type", "float32"), 0))

# 同步音频设备类型选择（阻止信号避免初始化时错误触发）
        use_microphone = self.config.get("audio.use_microphone", False)
        self.mic_radio.blockSignals(True)
        self.speaker_radio.blockSignals(True)
        self.mic_radio.setChecked(use_microphone)
        self.speaker_radio.setChecked(not use_microphone)
        self.mic_radio.blockSignals(False)
        self.speaker_radio.blockSignals(False)
        
        # 手动触发设备列表更新（因为阻止了信号）
        self._update_device_combo()

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
        self.audio_capture.model_download_started.connect(self._on_model_download_started)
        self.audio_capture.model_download_progress.connect(self._on_model_download_progress)
        self.audio_capture.model_download_finished.connect(self._on_model_download_finished)
        self.audio_capture.model_download_failed.connect(self._on_model_download_failed)

        # 连接 overlay 窗口的显示/隐藏信号
        self.overlay.visibilityChanged.connect(self._on_overlay_visibility_changed)
        
        # 连接 overlay 的监听控制信号
        self.overlay.listeningStarted.connect(self._on_overlay_listening_started)
        self.overlay.listeningStopped.connect(self._on_overlay_listening_stopped)
        self.overlay.transcriptionModeChanged.connect(self._on_overlay_transcription_mode_changed)
        self.overlay.listeningToggled.connect(self._on_overlay_listening_toggled)  # 全局快捷键切换监听

        # 连接 LLM 信号到槽函数
        self.token_signal.connect(self._on_token_update)
        self.complete_signal.connect(self._on_generation_complete)
        self.error_signal.connect(self._on_llm_error_slot)

        self.volume_timer = QTimer()
        self.volume_timer.timeout.connect(self._update_volume_display)
        self.volume_timer.start(100)

        self.caption_queue = []
        self.current_volume = 0.0
        self._on_overlay_transcription_mode_changed(self.overlay.is_manual_transcription_mode())
    
    def _select_resume(self):
        """选择 Markdown 文件"""
        # 获取当前路径作为起始目录
        current_path = self.resume_path_input.text() or ""
        start_dir = os.path.dirname(current_path) if current_path and os.path.exists(current_path) else ""
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择知识库文档", start_dir, "Markdown 文件 (*.md *.markdown);;所有文件 (*.*)"
        )
        
        if file_path:
            self._load_resume_from_path(file_path)
    
    def _on_resume_path_entered(self):
        """用户手动输入路径后按 Enter"""
        file_path = self.resume_path_input.text().strip()
        if file_path:
            self._load_resume_from_path(file_path)
    
    def _load_resume_from_path(self, file_path: str):
        """从指定路径加载文档"""
        # 验证文件存在
        if not os.path.exists(file_path):
            self._update_doc_status(False, "文件不存在")
            self.resume_summary_label.setText("⚠ 文件不存在，请检查路径")
            self.resume_summary_label.setStyleSheet(f"color: {ERROR}; font-size: 11px;")
            return
        
        # 验证文件扩展名
        if not file_path.lower().endswith(('.md', '.markdown')):
            self._update_doc_status(False, "文件格式错误")
            self.resume_summary_label.setText("⚠ 仅支持 Markdown 文件 (.md)")
            self.resume_summary_label.setStyleSheet(f"color: {ERROR}; font-size: 11px;")
            return
        
        try:
            # 解析文档
            self.resume_data = parse_resume(file_path)
            
            # 更新 UI
            self.resume_path_input.setText(file_path)
            self._update_doc_status(True, "文档已加载")
            
            # 显示摘要
            summary = f"✓ {self.resume_data.get('name', '未知')} | "
            summary += f"技能 {len(self.resume_data.get('skills', []))} 项 | "
            summary += f"经历 {len(self.resume_data.get('experience', []))} 段"
            self.resume_summary_label.setText(summary)
            self.resume_summary_label.setStyleSheet(f"color: {SUCCESS}; font-size: 11px;")
            
            # 保存路径到配置
            self.config.set("document.path", file_path)
            log_system(f"文档已加载并保存路径: {file_path}", logging.INFO)
            
        except Exception as e:
            self._update_doc_status(False, "解析失败")
            self.resume_summary_label.setText(f"⚠ 解析失败: {str(e)}")
            self.resume_summary_label.setStyleSheet(f"color: {ERROR}; font-size: 11px;")
            QMessageBox.warning(self, "解析失败", f"无法解析文档：{str(e)}")
    
    def _update_doc_status(self, is_valid: bool, tooltip: str = ""):
        """更新文档状态指示器"""
        self.doc_status_btn.setVisible(True)
        if is_valid:
            self.doc_status_btn.setText("✓")
            self.doc_status_btn.setStyleSheet(f"""
                QToolButton {{
                    border: none;
                    background: transparent;
                    color: {SUCCESS};
                    font-size: 16px;
                    font-weight: bold;
                }}
            """)
        else:
            self.doc_status_btn.setText("⚠")
            self.doc_status_btn.setStyleSheet(f"""
                QToolButton {{
                    border: none;
                    background: transparent;
                    color: {ERROR};
                    font-size: 16px;
                    font-weight: bold;
                }}
            """)
        self.doc_status_btn.setToolTip(tooltip)
    
    def _clear_resume(self):
        """清除文档"""
        self.resume_data = None
        self.resume_path_input.clear()
        self.doc_status_btn.setVisible(False)
        self.resume_summary_label.setText("")
        
        # 清除配置中的路径
        self.config.set("document.path", "")
        log_system("文档已清除", logging.INFO)
    
    def _load_saved_document(self):
        """启动时自动加载保存的文档"""
        saved_path = self.config.document_path
        if saved_path and os.path.exists(saved_path):
            log_system(f"自动加载保存的文档: {saved_path}", logging.INFO)
            self._load_resume_from_path(saved_path)
        elif saved_path:
            # 路径存在但文件不存在
            self.resume_path_input.setText(saved_path)
            self._update_doc_status(False, "文件不存在")
            self.resume_summary_label.setText("⚠ 保存的文件不存在，请重新选择")
            self.resume_summary_label.setStyleSheet(f"color: {ERROR}; font-size: 11px;")
    
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
            self.caption_status.setText("字幕窗口：已隐藏（点击字幕按钮或 Ctrl+F4 重新显示）")
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
            self.caption_status.setText("字幕窗口：已隐藏（点击字幕按钮或 Ctrl+F4 重新显示）")
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
                    base_url = "http://127.0.0.1:1234"

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
                from PySide6.QtGui import QColor, QBrush
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

        from PySide6.QtCore import QTimer
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
        from PySide6.QtCore import QTimer
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
        is_output = self.speaker_radio.isChecked()
        devices = self.audio_output_devices if is_output else self.audio_devices
        current_index = self.audio_device_combo.currentIndex()
        if 0 <= current_index < len(devices):
            device_index = devices[current_index]['index']
            if is_output:
                self.config.set("audio.output_device_index", device_index)
            else:
                self.config.set("audio.input_device_index", device_index)

        # 保存设备类型配置
        self.config.set("audio.use_microphone", not is_output)

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
            self.mic_radio.setEnabled(False)
            self.speaker_radio.setEnabled(False)
            self.refresh_devices_btn.setEnabled(False)
            # LLM 配置在录音时仍可修改
            # self.llm_combo.setEnabled(False)
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
            self.mic_radio.setEnabled(True)
            self.speaker_radio.setEnabled(True)
            self.refresh_devices_btn.setEnabled(True)
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
        self.transcription_log_data.append(log_entry)  # 存储到列表
        
        # 同时添加回答日志占位（稍后填充）
        self._pending_answer_log_index = len(self.transcription_log_data)

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
        self._stt_download_canceled = False
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
        # 注意：不要在这里调用 _show_download_dialog()，只有在真正需要下载时才显示下载对话框

    def _show_download_dialog(self):
        if self._stt_download_canceled:
            return
        if hasattr(self, "_stt_download_dialog") and self._stt_download_dialog:
            self._stt_download_dialog.show()
            return
        dialog = QProgressDialog("正在准备 STT 模型...", "取消下载", 0, 100, self)
        dialog.setWindowTitle("STT 模型下载")
        dialog.setAutoClose(False)
        dialog.setAutoReset(False)
        dialog.setMinimumDuration(0)
        dialog.setValue(0)
        dialog.canceled.connect(self._on_stt_download_canceled)
        dialog.show()
        self._stt_download_dialog = dialog

    def _on_model_download_started(self, repo_id: str):
        if self._stt_download_canceled:
            return
        self._show_download_dialog()
        self._stt_download_dialog.setLabelText(
            f"首次使用需要下载模型：{repo_id}\n提示：大文件下载阶段进度可能短时不变化。"
        )
        self._stt_download_dialog.setValue(0)

    def _on_model_download_progress(self, progress: float, speed_text: str):
        if self._stt_download_canceled:
            return
        self._show_download_dialog()
        self._stt_download_dialog.setValue(int(progress))
        self._stt_download_dialog.setLabelText(
            f"正在下载 STT 模型... {progress:.1f}% ({speed_text})\n大文件下载时百分比可能暂时不变。"
        )

    def _on_model_download_finished(self):
        if hasattr(self, "_stt_download_dialog") and self._stt_download_dialog:
            self._stt_download_dialog.setValue(100)
            self._stt_download_dialog.setLabelText("STT 模型下载完成，正在加载...")
            self._stt_download_dialog.hide()
        self._stt_download_canceled = False

    def _on_model_download_failed(self, error_msg: str):
        if hasattr(self, "_stt_download_dialog") and self._stt_download_dialog:
            self._stt_download_dialog.hide()
        if self._stt_download_canceled:
            self._stt_download_canceled = False
            return
        QMessageBox.warning(self, "STT 模型下载失败", f"请检查网络或镜像配置。\n{error_msg}")

    def _on_stt_download_canceled(self):
        self._stt_download_canceled = True
        if hasattr(self, "audio_capture") and self.audio_capture:
            self.audio_capture.request_cancel_download()
        if hasattr(self, "_stt_download_dialog") and self._stt_download_dialog:
            self._stt_download_dialog.setLabelText("正在取消下载，请稍候...")

    def _on_model_loaded(self):
        """模型加载完成 - 更新为监听中状态"""
        self.is_model_loading = False
        log_system("模型加载完成", logging.INFO)
        if hasattr(self, "_stt_download_dialog") and self._stt_download_dialog:
            self._stt_download_dialog.hide()
        self._update_ui_state()  # 恢复正常状态
        # 字幕窗口会在点击"开始监听"按钮，模型加载完成后显示
        self.overlay.show()
        self.caption_status.setText("字幕窗口：显示中（拖动顶部灰色条移动窗口，双击隐藏）")
        self.caption_toggle_btn.setText("📑 隐藏")
        # 启用 overlay 的监听按钮（模型已加载）
        if hasattr(self, "audio_capture") and self.audio_capture:
            self.overlay.set_listen_button_enabled(self.overlay.is_manual_transcription_mode())
            if not self.overlay.is_manual_transcription_mode():
                # 自动模式：模型就绪后立即进入自动分句监听
                self.audio_capture.set_manual_mode(False)
                self.status_label.setText("● 自动转录中...")
                self.status_label.setStyleSheet(f"color: {STATUS_COLORS['listening']};")

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
            self.caption_status.setText("字幕窗口：已隐藏（点击字幕按钮或 Ctrl+F4 重新显示）")
            self.caption_toggle_btn.setText("📑 字幕")
    
    def _on_overlay_listening_started(self):
        """overlay 开始监听 - 启动手动录音"""
        if not self.overlay.is_manual_transcription_mode():
            return
        # 检查模型是否是否已加载
        if self.is_model_loading or self.audio_capture.stt_model is None:
            QMessageBox.warning(self, "提示", "模型正在加载中，请稍后再试")
            log_system("录音失败：模型未加载", logging.WARNING)
            return

        # 先启动音频捕获（如果还没启动）
        if not self.audio_capture.is_running():
            self.audio_capture.start()
        # 清空之前的音频缓冲区（避免收到模型加载期间收集的音频）
        with self.audio_capture._audio_buffer_lock:
            self.audio_capture._audio_buffer = []
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
        if not self.overlay.is_manual_transcription_mode():
            return
        # 停止录音（会自动触发转录）
        self.audio_capture.stop_recording()
        self.status_label.setText("● 已停止")
        self.status_label.setStyleSheet(f"color: {STATUS_COLORS['idle']};")

    def _on_overlay_transcription_mode_changed(self, manual_mode: bool):
        """字幕窗口切换手动/自动转录模式"""
        print(f"[MainWindow] _on_overlay_transcription_mode_changed 被调用，manual_mode={manual_mode}", flush=True)
        self.audio_capture.set_manual_mode(manual_mode)
        self.overlay.set_listen_button_enabled(self.audio_capture.is_running() and manual_mode)

        if manual_mode:
            if self.audio_capture._recording:
                self.audio_capture.stop_recording()
            self.status_label.setText("● 手动转录模式")
            self.status_label.setStyleSheet(f"color: {STATUS_COLORS['idle']};")
        else:
            # 自动模式：无论是否运行都更新状态栏
            if self.audio_capture.is_running() and self.audio_capture.stt_model is not None:
                self.status_label.setText("● 自动转录中...")
                self.status_label.setStyleSheet(f"color: {STATUS_COLORS['listening']};")
            else:
                self.status_label.setText("● 自动模式（未启动）")
                self.status_label.setStyleSheet(f"color: {STATUS_COLORS['idle']};")

    def _on_overlay_listening_toggled(self):
        """全局快捷键 Ctrl+F8 切换监听状态"""
        print("[MainWindow] _on_overlay_listening_toggled 被调用", flush=True)
        
        # 检查音频捕获是否运行
        if not self.audio_capture.is_running():
            # 首次启动：启动音频捕获并开始录音
            print("[MainWindow] 音频捕获未运行，启动并开始录音", flush=True)
            self._update_config_from_ui()
            is_valid, error_msg = self.config.validate()
            if not is_valid:
                QMessageBox.warning(self, "配置错误", error_msg)
                return
            self.audio_capture.start()
            # 同步 overlay 状态
            self.overlay._listening = True
            self.overlay.listen_btn.setText("■ 停止监听")
            self.overlay.listen_btn.setStyleSheet(self.overlay._listen_button_stylesheet())
            return
        
        # 音频捕获已运行，切换录音状态
        if self.audio_capture._recording:
            # 停止录音
            print("[MainWindow] 正在录音，停止", flush=True)
            self.audio_capture.stop_recording()
            # 同步 overlay 状态
            self.overlay._listening = False
            self.overlay.listen_btn.setText("▶ 开始监听")
            self.overlay.listen_btn.setStyleSheet(self.overlay._listen_button_stylesheet())
            # 注意：不隐藏字幕窗口，让用户继续查看
        else:
            # 开始录音（手动模式）
            print("[MainWindow] 未录音，开始录音", flush=True)
            self.audio_capture.set_manual_mode(True)
            self.audio_capture._recording = True
            # 同步 overlay 状态
            self.overlay._listening = True
            self.overlay.listen_btn.setText("■ 停止监听")
            self.overlay.listen_btn.setStyleSheet(self.overlay._listen_button_stylesheet())

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

    @Slot(str, int)
    def _on_token_update(self, token: str, page_index: int):
        """处理LLM token更新（在主线程中调用）"""
        # 获取当前显示的文本并追加新token
        current_text = self.overlay.caption_history.pages[page_index]["answer"] if 0 <= page_index < len(self.overlay.caption_history.pages) else ""
        new_text = current_text + token
        
        # 过滤掉思考内容（<think>...</think> 标签）
        # 移除 <think>...</think> 标签及其内容
        new_text = re.sub(r'<think>.*?</think>', '', new_text, flags=re.DOTALL)
        # 移除未闭合的 <think> 标签开头（等待后续 token）
        new_text = re.sub(r'<think>.*', '', new_text)
        
        self.overlay.caption_history.update_answer_streaming(new_text, page_index)

    @Slot(str)
    def _on_generation_complete(self, answer: str):
        """生成完成 - 更新状态并清理思考内容"""
        # 调试：打印原始答案
        print(f"[COMPLETE_DEBUG] raw answer length: {len(answer)}", flush=True)
        if len(answer) > 100:
            print(f"[COMPLETE_DEBUG] first 100 chars: '{answer[:100]}'", flush=True)
        
        # 最终清理：确保所有思考内容都被移除
        # 移除 ALSE...ALSE 标签及其内容
        clean_answer = re.sub(r'ALSE.*?ALSE', '', answer, flags=re.DOTALL)
        # 移除未闭合的 ALSE 标签
        clean_answer = re.sub(r'ALSE.*', '', clean_answer)
        # 移除可能的残留标签
        clean_answer = re.sub(r'</?ALSE>', '', clean_answer)
        
        # 格式2: <tool_call>...ྎ（DeepSeek格式）
        clean_answer = re.sub(r'ALSE.*?ALSE', '', clean_answer, flags=re.DOTALL)
        clean_answer = re.sub(r'ALSE.*', '', clean_answer)
        
        # 格式3: <|thought|>...<|/thought|>
        clean_answer = re.sub(r'<\|thought\|>.*?<\|/thought\|>', '', clean_answer, flags=re.DOTALL)
        clean_answer = re.sub(r'<\|thought\|>.*', '', clean_answer)
        
        # 格式4: <|reasoning|>...<|/reasoning|>
        clean_answer = re.sub(r'<\|reasoning\|>.*?<\|/reasoning\|>', '', clean_answer, flags=re.DOTALL)
        clean_answer = re.sub(r'<\|reasoning\|>.*', '', clean_answer)
        
        # 格式5: [思考]...[/思考] 或 【思考】...【/思考】
        clean_answer = re.sub(r'\[思考\].*?\[/思考\]', '', clean_answer, flags=re.DOTALL)
        clean_answer = re.sub(r'【思考】.*?【/思考】', '', clean_answer, flags=re.DOTALL)
        
        # 如果清理后的答案与当前字幕不同，更新字幕
        if clean_answer != answer:
            current_page = self.overlay.caption_history.current_page
            if 0 <= current_page < len(self.overlay.caption_history.pages):
                self.overlay.caption_history.update_answer_streaming(clean_answer, current_page)
        
        self.status_label.setText("● 就绪")
        self.status_label.setStyleSheet(f"color: {STATUS_COLORS['idle']};")

    @Slot(str)
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
        self.transcription_log_data.clear()
    
    def _open_transcription_log(self):
        """打开转录日志对话框"""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton
        
        dialog = QDialog(self)
        dialog.setWindowTitle("转录日志")
        dialog.setMinimumSize(500, 400)
        
        layout = QVBoxLayout(dialog)
        
        log_text = QTextEdit()
        log_text.setReadOnly(True)
        log_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {BACKGROUND};
                color: {TEXT_SECONDARY};
                border: 1px solid {BORDER_SUBTLE};
                border-radius: 4px;
                padding: 8px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
            }}
        """)
        
        # 显示所有日志
        if self.transcription_log_data:
            log_text.setText("\n".join(self.transcription_log_data))
        else:
            log_text.setPlaceholderText("暂无转录日志...")
        
        layout.addWidget(log_text)
        
        # 清空按钮
        clear_btn = QPushButton("清空日志")
        clear_btn.setStyleSheet(DANGER_BUTTON)
        clear_btn.clicked.connect(lambda: (self.transcription_log_data.clear(), log_text.clear()))
        layout.addWidget(clear_btn)
        
        dialog.exec()

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
            # 重新创建 LLM 客户端以应用新配置
            self.llm_client.switch_mode()
            QMessageBox.information(self, "保存成功", "配置已保存到 config.yaml")
            log_system("配置已保存", logging.INFO)
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"无法保存配置：{str(e)}")
            log_system(f"保存配置失败：{str(e)}", logging.ERROR)
    
    def _open_advanced_settings(self):
        """打开高级设置对话框"""
        dialog = AdvancedSettingsDialog(self.config, self)
        dialog.exec()
    
    def closeEvent(self, event):
        """关闭窗口时的处理"""
        if self.audio_capture.is_running():
            self.audio_capture.stop()
        log_system("程序关闭，已停止音频捕获和音量监控", logging.INFO)
        event.accept()
