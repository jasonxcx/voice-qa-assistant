"""
主窗口 - 简历导入、配置、控制
"""
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QGroupBox,
    QComboBox, QLineEdit, QCheckBox, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer
from typing import Optional, Dict, Any

from core.config import Config
from core.resume_parser import ResumeParser, parse_resume
from ui.styles import MAIN_WINDOW_STYLESHEET, STATUS_COLORS


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self, overlay_window, audio_capture, llm_client):
        super().__init__()
        self.overlay = overlay_window
        self.audio_capture = audio_capture
        self.llm_client = llm_client
        self.config = audio_capture.config
        
        self.resume_data: Optional[Dict[str, Any]] = None
        
        self._init_ui()
        self._connect_signals()
    
    def _init_ui(self):
        """初始化 UI"""
        self.setWindowTitle("面试辅助工具")
        self.setMinimumSize(500, 600)
        self.setStyleSheet(MAIN_WINDOW_STYLESHEET)
        
        # 中央控件
        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        title_label = QLabel("🎯 面试辅助工具")
        title_label.setObjectName("titleLabel")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 状态
        self.status_label = QLabel("● 就绪")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # 简历导入
        resume_group = QGroupBox("简历导入")
        resume_layout = QVBoxLayout(resume_group)
        
        self.resume_path_label = QLabel("未选择简历文件")
        self.resume_path_label.setStyleSheet("color: #9AA0A6; padding: 8px;")
        resume_layout.addWidget(self.resume_path_label)
        
        select_btn = QPushButton("选择 Markdown 简历文件")
        select_btn.clicked.connect(self._select_resume)
        resume_layout.addWidget(select_btn)
        
        layout.addWidget(resume_group)
        
        # 大模型选择
        llm_group = QGroupBox("大模型设置")
        llm_layout = QVBoxLayout(llm_group)
        
        self.llm_combo = QComboBox()
        self.llm_combo.addItems(["通义千问 (云端)", "Ollama (本地)", "LM Studio (本地)"])
        self.llm_combo.currentIndexChanged.connect(self._on_llm_changed)
        llm_layout.addWidget(QLabel("模型:"))
        llm_layout.addWidget(self.llm_combo)
        
        # Ollama 配置
        self.ollama_url_input = QLineEdit()
        self.ollama_url_input.setPlaceholderText("http://localhost:11434")
        self.ollama_url_input.setText(self.config.ollama_url)
        llm_layout.addWidget(QLabel("Ollama URL:"))
        llm_layout.addWidget(self.ollama_url_input)
        
        layout.addWidget(llm_group)
        
        # 音频设置
        audio_group = QGroupBox("音频设置")
        audio_layout = QVBoxLayout(audio_group)
        
        self.device_index_input = QLineEdit()
        self.device_index_input.setText(str(self.config.audio_device_index))
        audio_layout.addWidget(QLabel("音频设备索引:"))
        audio_layout.addWidget(self.device_index_input)
        
        audio_layout.addWidget(QLabel(
            "提示：运行 <code>python -m sounddevice</code> 查看设备列表",
            stylesheet="color: #9AA0A6; font-size: 12px;"
        ))
        
        layout.addWidget(audio_group)
        
        # 控制按钮
        button_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("开始监听")
        self.start_btn.setMinimumHeight(50)
        self.start_btn.clicked.connect(self._toggle_listening)
        button_layout.addWidget(self.start_btn)
        
        layout.addLayout(button_layout)
        
        # 使用说明
        help_group = QGroupBox("使用说明")
        help_layout = QVBoxLayout(help_group)
        help_layout.addWidget(QLabel(
            "1. 导入 Markdown 格式简历\n"
            "2. 选择大模型（云端/本地）\n"
            "3. 配置音频设备（VB-Cable）\n"
            "4. 点击开始，字幕窗口将自动显示\n\n"
            "提示：字幕窗口始终置顶且鼠标穿透，不会遮挡会议软件"
        ))
        layout.addWidget(help_group)
        
        # 更新 UI 状态
        self._update_ui_state()
    
    def _connect_signals(self):
        """连接信号"""
        # 音频捕获信号
        self.audio_capture.transcription_ready.connect(self._on_transcription_ready)
        self.audio_capture.real_time_update.connect(self._on_realtime_update)
        self.audio_capture.recording_started.connect(self._on_recording_started)
        self.audio_capture.recording_stopped.connect(self._on_recording_stopped)
        self.audio_capture.error_occurred.connect(self._on_error)
        
        # 字幕更新定时器
        self.caption_timer = QTimer()
        self.caption_timer.timeout.connect(self._process_caption_queue)
        self.caption_timer.start(100)  # 100ms 刷新一次
        
        self.caption_queue = []
    
    def _select_resume(self):
        """选择简历文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择简历文件",
            "",
            "Markdown 文件 (*.md);;所有文件 (*.*)"
        )
        
        if file_path:
            try:
                self.resume_data = parse_resume(file_path)
                self.resume_path_label.setText(f"✓ {file_path}")
                self.resume_path_label.setStyleSheet("color: #4CAF50; padding: 8px;")
                
                # 显示简历摘要
                summary = f"已解析：{self.resume_data.get('name', '未知')} | "
                summary += f"技能：{len(self.resume_data.get('skills', []))} 项 | "
                summary += f"经历：{len(self.resume_data.get('experience', []))} 段"
                self.resume_path_label.setToolTip(summary)
                
            except Exception as e:
                QMessageBox.critical(self, "解析失败", f"简历解析失败：{str(e)}")
    
    def _on_llm_changed(self, index):
        """切换大模型"""
        mode_map = {0: "qwen", 1: "ollama", 2: "lmstudio"}
        mode = mode_map.get(index, "qwen")
        
        try:
            self.llm_client.switch_mode(mode)
            self._update_ui_state()
        except Exception as e:
            QMessageBox.critical(self, "切换失败", str(e))
    
    def _toggle_listening(self):
        """切换监听状态"""
        if self.audio_capture.is_running():
            self.audio_capture.stop()
        else:
            # 验证配置
            is_valid, error_msg = self.config.validate()
            if not is_valid:
                QMessageBox.warning(self, "配置错误", error_msg)
                return
            
            self.audio_capture.start()
    
    def _update_ui_state(self):
        """更新 UI 状态"""
        is_running = self.audio_capture.is_running()
        
        if is_running:
            self.start_btn.setText("停止监听")
            self.start_btn.setStyleSheet("background-color: #F44336;")
        else:
            self.start_btn.setText("开始监听")
            self.start_btn.setStyleSheet("")
        
        # 更新状态标签
        mode = self.config.llm_mode
        mode_names = {"qwen": "通义千问", "ollama": "Ollama", "lmstudio": "LM Studio"}
        self.status_label.setText(f"● 就绪 - {mode_names.get(mode, mode)}")
        self.status_label.setStyleSheet(f"color: {STATUS_COLORS['idle']};")
    
    def _on_transcription_ready(self, text: str):
        """转录文本就绪"""
        self.caption_queue.append(("question", text))
        self.status_label.setText("● 正在生成回答...")
        self.status_label.setStyleSheet(f"color: {STATUS_COLORS['generating']};")
    
    def _on_realtime_update(self, text: str):
        """实时转录更新"""
        # 显示正在听写的状态
        self.status_label.setText(f"● 听写中：{text[:50]}...")
        self.status_label.setStyleSheet(f"color: {STATUS_COLORS['listening']};")
    
    def _on_recording_started(self):
        """录音开始"""
        self._update_ui_state()
        self.status_label.setText("● 监听中...")
        self.status_label.setStyleSheet(f"color: {STATUS_COLORS['listening']};")
    
    def _on_recording_stopped(self):
        """录音停止"""
        self._update_ui_state()
    
    def _on_error(self, error_msg: str):
        """错误处理"""
        self.status_label.setText("● 错误")
        self.status_label.setStyleSheet(f"color: {STATUS_COLORS['error']};")
        QMessageBox.warning(self, "错误", error_msg)
    
    async def _process_caption_queue(self):
        """处理字幕队列"""
        if not self.caption_queue:
            return
        
        item_type, text = self.caption_queue.pop(0)
        
        if item_type == "question":
            # 显示问题
            self.overlay.update_caption(f"❓ {text}")
            
            # 异步生成回答
            import asyncio
            asyncio.ensure_future(self._generate_and_show_answer(text))
    
    async def _generate_and_show_answer(self, question: str):
        """生成并显示回答"""
        try:
            answer = await self.llm_client.generate_answer(question, self.resume_data)
            self.overlay.update_caption(f"💡 {answer}")
            self.status_label.setText("● 就绪")
            self.status_label.setStyleSheet(f"color: {STATUS_COLORS['idle']};")
        except Exception as e:
            self.overlay.update_caption(f"⚠️ 生成失败：{str(e)}")
    
    def closeEvent(self, event):
        """关闭窗口时的处理"""
        if self.audio_capture.is_running():
            self.audio_capture.stop()
        event.accept()
