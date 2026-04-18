"""
高级设置对话框 - 包含所有未暴露在主界面的配置项
"""
import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QFormLayout, QLabel, QLineEdit, QSpinBox, QDoubleSpinBox,
    QComboBox, QPushButton, QGroupBox, QCheckBox, QMessageBox
)
from PySide6.QtCore import Qt

from ui.styles import (
    BACKGROUND, SURFACE, SURFACE_HOVER, BORDER_SUBTLE, TEXT_PRIMARY,
    TEXT_SECONDARY, ACCENT_PRIMARY, PRIMARY_BUTTON, SECONDARY_BUTTON
)


class AdvancedSettingsDialog(QDialog):
    """高级设置对话框"""
    
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("高级设置")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        self._init_ui()
        self._load_settings()
    
    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        
        # 使用 Tab 组织设置
        tabs = QTabWidget()
        tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {BORDER_SUBTLE};
                background-color: {BACKGROUND};
            }}
            QTabBar::tab {{
                background-color: {SURFACE};
                color: {TEXT_SECONDARY};
                padding: 8px 16px;
                border-radius: 4px;
            }}
            QTabBar::tab:selected {{
                background-color: {ACCENT_PRIMARY};
                color: {TEXT_PRIMARY};
            }}
        """)
        
        # Tab 1: LLM 高级设置
        llm_tab = self._create_llm_tab()
        tabs.addTab(llm_tab, "LLM 高级")
        
        # Tab 2: STT 高级设置
        stt_tab = self._create_stt_tab()
        tabs.addTab(stt_tab, "STT 高级")
        
        # Tab 3: UI/热键设置
        ui_tab = self._create_ui_tab()
        tabs.addTab(ui_tab, "显示/热键")
        
        layout.addWidget(tabs)
        
        # 按钮
        btn_layout = QHBoxLayout()
        
        save_btn = QPushButton("保存")
        save_btn.setStyleSheet(PRIMARY_BUTTON)
        save_btn.clicked.connect(self._save_settings)
        btn_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet(SECONDARY_BUTTON)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
    
    def _create_llm_tab(self) -> QWidget:
        """创建 LLM 高级设置 Tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 生成参数
        gen_group = QGroupBox("生成参数")
        gen_group.setStyleSheet(f"""
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
        
        # 提示词设置
        prompt_group = QGroupBox("提示词模板")
        prompt_group.setStyleSheet(gen_group.styleSheet())
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
        layout.addStretch()
        
        return widget
    
    def _create_stt_tab(self) -> QWidget:
        """创建 STT 高级设置 Tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 自动分句参数
        auto_group = QGroupBox("自动分句参数（仅自动模式生效）")
        auto_group.setStyleSheet(f"""
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
        
        # 下载/语言设置
        download_group = QGroupBox("下载与语言")
        download_group.setStyleSheet(auto_group.styleSheet())
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
        layout.addStretch()
        
        return widget
    
    def _create_ui_tab(self) -> QWidget:
        """创建显示和热键设置 Tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Overlay 设置
        overlay_group = QGroupBox("字幕窗口")
        overlay_group.setStyleSheet(f"""
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
        overlay_form = QFormLayout(overlay_group)
        
        self.overlay_height_spin = QSpinBox()
        self.overlay_height_spin.setRange(100, 800)
        self.overlay_height_spin.setToolTip("字幕窗口高度")
        overlay_form.addRow("窗口高度:", self.overlay_height_spin)
        
        self.overlay_width_spin = QDoubleSpinBox()
        self.overlay_width_spin.setRange(0.5, 1.0)
        self.overlay_width_spin.setSingleStep(0.05)
        self.overlay_width_spin.setDecimals(2)
        self.overlay_width_spin.setToolTip("相对屏幕宽度比例")
        overlay_form.addRow("宽度比例:", self.overlay_width_spin)
        
        self.overlay_radius_spin = QSpinBox()
        self.overlay_radius_spin.setRange(0, 24)
        self.overlay_radius_spin.setToolTip("窗口圆角半径")
        overlay_form.addRow("圆角半径:", self.overlay_radius_spin)
        
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 40)
        self.font_size_spin.setToolTip("字幕字体大小")
        overlay_form.addRow("字体大小:", self.font_size_spin)
        
        layout.addWidget(overlay_group)
        
        # 热键设置
        hotkey_group = QGroupBox("快捷键")
        hotkey_group.setStyleSheet(overlay_group.styleSheet())
        hotkey_form = QFormLayout(hotkey_group)
        
        self.hotkey_visibility_input = QLineEdit()
        self.hotkey_visibility_input.setToolTip("显示/隐藏字幕窗口")
        hotkey_form.addRow("显示/隐藏:", self.hotkey_visibility_input)
        
        self.hotkey_mode_input = QLineEdit()
        self.hotkey_mode_input.setToolTip("切换自动/手动模式")
        hotkey_form.addRow("切换模式:", self.hotkey_mode_input)
        
        self.hotkey_listen_input = QLineEdit()
        self.hotkey_listen_input.setToolTip("开始/结束监听")
        hotkey_form.addRow("监听控制:", self.hotkey_listen_input)
        
        self.hotkey_prev_input = QLineEdit()
        self.hotkey_prev_input.setToolTip("上一条字幕")
        hotkey_form.addRow("上一条:", self.hotkey_prev_input)
        
        self.hotkey_next_input = QLineEdit()
        self.hotkey_next_input.setToolTip("下一条字幕")
        hotkey_form.addRow("下一条:", self.hotkey_next_input)
        
        layout.addWidget(hotkey_group)
        layout.addStretch()
        
        return widget
    
    def _load_settings(self):
        """从 config 加载设置到 UI"""
        # LLM
        self.temp_spin.setValue(self.config.get("llm.generation.temperature", 0.3))
        self.max_tokens_spin.setValue(self.config.get("llm.generation.max_completion_tokens", 500))
        self.max_tokens_stream_spin.setValue(self.config.get("llm.generation.max_completion_tokens_stream", 1000))
        self.reasoning_combo.setCurrentText(self.config.get("llm.generation.reasoning_effort", "none"))
        self.prompt_base_input.setText(self.config.get("llm.prompts.base", ""))
        self.prompt_words_input.setText(self.config.get("llm.prompts.words", ""))
        self.prompt_theme_input.setText(self.config.get("llm.prompts.theme", ""))
        
        # STT
        self.volume_threshold_spin.setValue(self.config.get("stt.auto.volume_threshold", 0.015))
        self.voice_ratio_spin.setValue(self.config.get("stt.auto.voice_ratio", 3.0))
        self.silence_ratio_spin.setValue(self.config.get("stt.auto.silence_ratio", 1.8))
        self.noise_alpha_spin.setValue(self.config.get("stt.auto.noise_alpha", 0.08))
        self.pause_seconds_spin.setValue(self.config.get("stt.auto.pause_seconds", 0.8))
        self.min_sentence_spin.setValue(self.config.get("stt.auto.min_sentence_seconds", 2.0))
        self.max_sentence_spin.setValue(self.config.get("stt.auto.max_sentence_seconds", 8.0))
        self.resume_chunks_spin.setValue(self.config.get("stt.auto.resume_voice_chunks", 2))
        
        self.download_mirror_input.setText(self.config.get("stt.download.mirror", ""))
        self.cache_dir_input.setText(self.config.get("stt.download.cache_dir", ""))
        self.stt_language_combo.setCurrentText(self.config.get("stt.local.language", "zh"))
        self.stt_hotwords_input.setText(self.config.get("stt.hotwords", ""))
        self.stt_model_path_input.setText(self.config.get("stt.local.model_path", ""))
        
        # UI
        self.overlay_height_spin.setValue(self.config.get("ui.overlay_height", 500))
        self.overlay_width_spin.setValue(self.config.get("ui.overlay_width_ratio", 0.85))
        self.overlay_radius_spin.setValue(self.config.get("ui.overlay_border_radius", 12))
        self.font_size_spin.setValue(self.config.get("ui.font_size", 12))
        
        self.hotkey_visibility_input.setText(self.config.get("ui.keyboard_hotkey.overlay_visibility", "Ctrl+F4"))
        self.hotkey_mode_input.setText(self.config.get("ui.keyboard_hotkey.transcription_mode", "Ctrl+F6"))
        self.hotkey_listen_input.setText(self.config.get("ui.keyboard_hotkey.listening_toggled", "Ctrl+F8"))
        self.hotkey_prev_input.setText(self.config.get("ui.keyboard_hotkey.prev_caption", "Ctrl+F7"))
        self.hotkey_next_input.setText(self.config.get("ui.keyboard_hotkey.next_caption", "Ctrl+F9"))
    
    def _save_settings(self):
        """保存设置到 config"""
        # LLM
        self.config.set("llm.generation.temperature", self.temp_spin.value())
        self.config.set("llm.generation.max_completion_tokens", self.max_tokens_spin.value())
        self.config.set("llm.generation.max_completion_tokens_stream", self.max_tokens_stream_spin.value())
        self.config.set("llm.generation.reasoning_effort", self.reasoning_combo.currentText())
        self.config.set("llm.prompts.base", self.prompt_base_input.text())
        self.config.set("llm.prompts.words", self.prompt_words_input.text())
        self.config.set("llm.prompts.theme", self.prompt_theme_input.text())
        
        # STT
        self.config.set("stt.auto.volume_threshold", self.volume_threshold_spin.value())
        self.config.set("stt.auto.voice_ratio", self.voice_ratio_spin.value())
        self.config.set("stt.auto.silence_ratio", self.silence_ratio_spin.value())
        self.config.set("stt.auto.noise_alpha", self.noise_alpha_spin.value())
        self.config.set("stt.auto.pause_seconds", self.pause_seconds_spin.value())
        self.config.set("stt.auto.min_sentence_seconds", self.min_sentence_spin.value())
        self.config.set("stt.auto.max_sentence_seconds", self.max_sentence_spin.value())
        self.config.set("stt.auto.resume_voice_chunks", self.resume_chunks_spin.value())
        
        self.config.set("stt.download.mirror", self.download_mirror_input.text())
        self.config.set("stt.download.cache_dir", self.cache_dir_input.text())
        self.config.set("stt.local.language", self.stt_language_combo.currentText())
        self.config.set("stt.hotwords", self.stt_hotwords_input.text())
        self.config.set("stt.local.model_path", self.stt_model_path_input.text())
        
        # UI
        self.config.set("ui.overlay_height", self.overlay_height_spin.value())
        self.config.set("ui.overlay_width_ratio", self.overlay_width_spin.value())
        self.config.set("ui.overlay_border_radius", self.overlay_radius_spin.value())
        self.config.set("ui.font_size", self.font_size_spin.value())
        
        self.config.set("ui.keyboard_hotkey.overlay_visibility", self.hotkey_visibility_input.text())
        self.config.set("ui.keyboard_hotkey.transcription_mode", self.hotkey_mode_input.text())
        self.config.set("ui.keyboard_hotkey.listening_toggled", self.hotkey_listen_input.text())
        self.config.set("ui.keyboard_hotkey.prev_caption", self.hotkey_prev_input.text())
        self.config.set("ui.keyboard_hotkey.next_caption", self.hotkey_next_input.text())
        
        QMessageBox.information(self, "保存成功", "设置已保存到 config.yaml")
        self.accept()