"""
透明字幕窗口 - 始终置顶、鼠标穿透、底部居中
"""
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QFont
from typing import Optional


class OverlayWindow(QWidget):
    """透明字幕窗口"""
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        self._init_ui()
        self._setup_window_flags()
    
    def _init_ui(self):
        """初始化 UI"""
        self.setObjectName("overlayWindow")
        
        # 获取屏幕尺寸
        screen = self.screen().geometry()
        overlay_height = self.config.overlay_height
        overlay_width = int(screen.width() * self.config.overlay_width_ratio)
        
        # 设置窗口尺寸
        self.setFixedSize(overlay_width, overlay_height)
        
        # 计算位置：底部居中
        x = screen.left() + (screen.width() - overlay_width) // 2
        y = screen.bottom() - overlay_height - 40
        self.move(x, y)
        
        # 布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 字幕标签
        self.caption_label = QLabel("", self)
        self.caption_label.setObjectName("captionLabel")
        self.caption_label.setAlignment(Qt.AlignCenter)
        self.caption_label.setWordWrap(True)
        self.caption_label.setStyleSheet(f"""
            color: #FFFFFF;
            font-size: {self.config.font_size}px;
            font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
            padding: 14px 18px;
            background-color: transparent;
        """)
        
        layout.addWidget(self.caption_label)
    
    def _setup_window_flags(self):
        """设置窗口标志：透明、置顶、鼠标穿透"""
        # 无边框
        self.setWindowFlags(
            Qt.FramelessWindowHint |      # 无边框
            Qt.WindowStaysOnTopHint |     # 始终置顶
            Qt.Tool                       # 不在任务栏显示
        )
        
        # 透明背景
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 鼠标穿透 - 关键！让鼠标事件传递给下层窗口
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        # 不获取焦点
        self.setFocusPolicy(Qt.NoFocus)
    
    def update_caption(self, text: str):
        """
        更新字幕内容
        
        Args:
            text: 要显示的字幕文本
        """
        self.caption_label.setText(text)
    
    def clear_caption(self):
        """清空字幕"""
        self.caption_label.clear()
    
    def set_position(self, x: Optional[int] = None, y: Optional[int] = None):
        """
        设置窗口位置
        
        Args:
            x: X 坐标，None 则保持当前值
            y: Y 坐标，None 则保持当前值
        """
        current_pos = self.pos()
        new_x = x if x is not None else current_pos.x()
        new_y = y if y is not None else current_pos.y()
        self.move(new_x, new_y)
    
    def reposition(self):
        """重新计算并设置位置（屏幕尺寸变化时调用）"""
        screen = self.screen().geometry()
        overlay_width = self.width()
        overlay_height = self.height()
        
        x = screen.left() + (screen.width() - overlay_width) // 2
        y = screen.bottom() - overlay_height - 40
        self.move(x, y)
    
    def showEvent(self, event):
        """窗口显示事件"""
        super().showEvent(event)
        self.reposition()
    
    def keyPressEvent(self, event):
        """键盘事件 - 支持快捷键"""
        if event.key() == Qt.Key_Escape:
            self.hide()
        super().keyPressEvent(event)
