"""
透明字幕窗口 - 带控制按钮和拖动条
特性：
- 背景完全透明
- 顶部拖动条（可拖动窗口，双击隐藏）
- 控制按钮：隐藏、字体变大、字体变小、上一条、下一条
- F12 快捷键显示/隐藏
- 鼠标拖动边缘调节窗口大小
- 显示"等待音频输入..."占位符
"""
from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
    QGraphicsDropShadowEffect, QSizeGrip
)
from PyQt5.QtCore import Qt, QPoint, QTimer, pyqtSignal, QEvent, QPropertyAnimation, QEasingCurve, QRect
from PyQt5.QtGui import QFont, QColor, QCursor
from collections import deque


class CaptionHistory(QWidget):
    """字幕历史记录组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.history = deque(maxlen=100)
        self.current_index = -1
        self._placeholder_text = "等待音频输入..."
        self._init_ui()

    def _init_ui(self):
        """初始化 UI"""
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAutoFillBackground(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        # 内容标签 - 初始显示占位符
        # 设置 minimumHeight 确保占位符可见
        self.content_label = QLabel(self._placeholder_text)
        self.content_label.setObjectName("contentLabel")
        self.content_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.content_label.setWordWrap(True)
        self.content_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.content_label.setMinimumHeight(60)  # 确保占位符可见
        self._set_placeholder_style()
        self._update_font()
        layout.addWidget(self.content_label, 1)  # 拉伸因子为 1

        # 翻页控制 - 固定在底部
        control_layout = QHBoxLayout()
        control_layout.setSpacing(6)

        self.prev_btn = QPushButton("◀")
        self.prev_btn.setToolTip("上一条")
        self.prev_btn.clicked.connect(self._show_previous)
        self.prev_btn.setFixedSize(32, 32)
        self.prev_btn.setStyleSheet(self._button_stylesheet())

        self.page_label = QLabel("0 / 0")
        self.page_label.setStyleSheet("color: rgba(255, 255, 255, 153); font-size: 11px;")
        self.page_label.setAlignment(Qt.AlignCenter)
        self.page_label.setFixedHeight(32)

        self.next_btn = QPushButton("▶")
        self.next_btn.setToolTip("下一条")
        self.next_btn.clicked.connect(self._show_next)
        self.next_btn.setFixedSize(32, 32)
        self.next_btn.setStyleSheet(self._button_stylesheet())

        control_layout.addWidget(self.prev_btn)
        control_layout.addWidget(self.page_label)
        control_layout.addWidget(self.next_btn)
        control_layout.addStretch()

        layout.addLayout(control_layout)

        self._update_buttons()

    def _button_stylesheet(self):
        return """
            QPushButton {
                background-color: rgba(255, 255, 255, 51);
                color: #FFFFFF;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 76);
            }
            QPushButton:disabled {
                background-color: rgba(255, 255, 255, 25);
                color: rgba(255, 255, 255, 102);
            }
        """

    def _set_placeholder_style(self):
        self.content_label.setStyleSheet("""
            color: rgba(255, 255, 255, 128);
            padding: 4px;
            line-height: 1.5;
            background: transparent;
            font-style: italic;
            font-size: 16px;
        """)

    def _set_content_style(self):
        self.content_label.setStyleSheet("""
            color: #FFFFFF;
            padding: 4px;
            line-height: 1.5;
            background: transparent;
        """)

    def _update_font(self, size=16):
        font = QFont("Microsoft YaHei", size)
        font.setWeight(QFont.Normal)
        self.content_label.setFont(font)

    def add_caption(self, text, caption_type="answer"):
        if len(self.history) == 0:
            self.content_label.setText("")
            self._set_content_style()

        color_map = {
            "listening": "#90CAF9",
            "answer": "#81C784",
            "normal": "#FFFFFF",
            "error": "#EF5350"
        }

        color = color_map.get(caption_type, "#FFFFFF")
        formatted = f'<span style="color: {color};">{text}</span>'

        self.history.append(formatted)
        self.current_index = len(self.history) - 1

        self._display_current()
        self._update_buttons()

    def _display_current(self):
        if self.current_index < 0 or self.current_index >= len(self.history):
            self.content_label.setText(self._placeholder_text)
            self._set_placeholder_style()
            self.page_label.setText("0 / 0")
            return

        # 只显示当前一条，不显示历史记录
        texts = [list(self.history)[self.current_index]]
        html = "<br/>".join(texts)
        self.content_label.setText(html)
        self.page_label.setText(f"{self.current_index + 1} / {len(self.history)}")

    def _show_previous(self):
        if self.current_index > 0:
            self.current_index -= 1
            self._display_current()
            self._update_buttons()

    def _show_next(self):
        if self.current_index < len(self.history) - 1:
            self.current_index += 1
            self._display_current()
            self._update_buttons()

    def _update_buttons(self):
        self.prev_btn.setEnabled(self.current_index > 0)
        self.next_btn.setEnabled(self.current_index < len(self.history) - 1)

    def clear(self):
        self.history.clear()
        self.current_index = -1
        self._display_current()
        self._update_buttons()

    def set_font_size(self, size):
        self._update_font(size)

    def enterEvent(self, event):
        """鼠标移入 - 更新按钮样式"""
        super().enterEvent(event)

    def leaveEvent(self, event):
        """鼠标移出"""
        super().leaveEvent(event)


class DragBar(QWidget):
    """顶部拖动条 - 支持拖动和双击隐藏"""

    double_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._dragging = False
        self._drag_position = QPoint()
        self._drag_started = False
        self._mouse_inside = False
        self._init_ui()
        self.setMouseTracking(True)

    def _init_ui(self):
        self.setFixedHeight(24)
        self._update_style()

        tip = QLabel("⇕ 拖动窗口  双击隐藏")
        tip.setAlignment(Qt.AlignCenter)
        tip.setStyleSheet("color: rgba(255, 255, 255, 102); font-size: 10px;")
        tip.setAttribute(Qt.WA_TransparentForMouseEvents)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(tip)

    def _update_style(self):
        """更新样式"""
        alpha = 51 if self._mouse_inside else 30
        self.setStyleSheet(f"""
            background-color: rgba(255, 255, 255, {alpha});
            border-top-left-radius: 12px;
            border-top-right-radius: 12px;
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._drag_started = False
            parent = self.parentWidget()
            if parent:
                self._drag_position = event.globalPos() - parent.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        # 检测鼠标是否在拖动条内
        rect = self.rect()
        self._mouse_inside = rect.contains(event.pos())

        if self._dragging and event.buttons() & Qt.LeftButton:
            self._drag_started = True
            parent = self.parentWidget()
            if parent:
                parent.move(event.globalPos() - self._drag_position)
            event.accept()
            return
        self._update_style()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = False
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.double_clicked.emit()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def enterEvent(self, event):
        self._mouse_inside = True
        self._update_style()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._mouse_inside = False
        self._update_style()
        super().leaveEvent(event)


class OverlayWindow(QWidget):
    """透明字幕窗口 - 支持鼠标调节大小"""

    # 可见性变化信号
    visibilityChanged = pyqtSignal(bool)
    sizes = [8, 12, 16, 20, 24, 28, 32, 36, 40]

    def __init__(self, config):
        super().__init__()
        self.config = config
        self._font_size = config.font_size
        self._drag_bar_hover = False
        self._resizing = False
        self._resize_rect = QRect()
        self._resize_handle_size = 20  # 调节区域大小
        self._mouse_in_resize_area = False
        self._init_ui()
        self._setup_window_flags()
        self.setMouseTracking(True)

        # 定时器检测鼠标位置
        self._hover_timer = QTimer()
        self._hover_timer.timeout.connect(self._check_hover_state)
        self._hover_timer.start(50)  # 更频繁的检测

    def _init_ui(self):
        self.setObjectName("overlayWindow")

        # 关键：设置完全透明
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAutoFillBackground(False)

        screen = self.screen().geometry()
        overlay_height = self.config.overlay_height
        overlay_width = int(screen.width() * self.config.overlay_width_ratio)

        self.setMinimumSize(400, 200)  # 设置最小尺寸
        self.resize(overlay_width, overlay_height)

        x = screen.left() + (screen.width() - overlay_width) // 2
        y = screen.bottom() - overlay_height - 40
        self.move(x, y)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. 顶部拖动条
        self.drag_bar = DragBar(self)
        self.drag_bar.double_clicked.connect(self._on_drag_bar_double_click)
        main_layout.addWidget(self.drag_bar)

        # 2. 内容区域 - 添加边框以便可见
        content_widget = QWidget()
        content_widget.setObjectName("contentWidget")
        content_widget.setStyleSheet("""
            QWidget#contentWidget {
                background-color: rgba(30, 30, 30, 200);
                border: 1px solid rgba(255, 255, 255, 64);
                border-bottom-left-radius: 12px;
                border-bottom-right-radius: 12px;
            }
        """)

        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(10, 10, 10, 10)
        content_layout.setSpacing(8)

        # 字幕历史 - 设置拉伸因子确保有足够空间
        self.caption_history = CaptionHistory(self)
        content_layout.addWidget(self.caption_history, 1)  # 拉伸因子为 1

        # 控制按钮行
        button_layout = QHBoxLayout()
        button_layout.setSpacing(6)

        self.hide_btn = QPushButton("📑 隐藏")
        self.hide_btn.setToolTip("隐藏窗口 (F12 重新显示)")
        self.hide_btn.setFixedHeight(28)
        self.hide_btn.clicked.connect(self._on_hide_clicked)
        self.hide_btn.setStyleSheet(self._hide_button_stylesheet())

        self.font_down_btn = QPushButton("Aa-")
        self.font_down_btn.setToolTip("缩小字体")
        self.font_down_btn.setFixedHeight(28)
        self.font_down_btn.clicked.connect(self._on_font_down_clicked)
        self.font_down_btn.setStyleSheet(self._action_button_stylesheet())

        self.font_up_btn = QPushButton("Aa+")
        self.font_up_btn.setToolTip("放大字体")
        self.font_up_btn.setFixedHeight(28)
        self.font_up_btn.clicked.connect(self._on_font_up_clicked)
        self.font_up_btn.setStyleSheet(self._action_button_stylesheet())

        # 添加大小调节提示标签
        self.resize_label = QLabel("⇘ 拖动右下角调节大小")
        self.resize_label.setAlignment(Qt.AlignCenter)
        self.resize_label.setStyleSheet("color: rgba(255, 255, 255, 102); font-size: 10px;")
        self.resize_label.setAttribute(Qt.WA_TransparentForMouseEvents)

        button_layout.addWidget(self.hide_btn)
        button_layout.addWidget(self.font_down_btn)
        button_layout.addWidget(self.font_up_btn)
        button_layout.addWidget(self.resize_label)
        button_layout.addStretch()

        content_layout.addLayout(button_layout)
        main_layout.addWidget(content_widget)

        # 阴影效果
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 128))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

    def _hide_button_stylesheet(self):
        return """
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
        """

    def _action_button_stylesheet(self):
        return """
            QPushButton {
                background-color: rgba(100, 150, 255, 100);
                color: #FFFFFF;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(100, 150, 255, 150);
            }
        """

    def _setup_window_flags(self):
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool |
            Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.StrongFocus)

    def _on_drag_bar_double_click(self):
        """拖动条双击"""
        self.hide()

    def _check_hover_state(self):
        """检测鼠标悬停状态"""
        if not self.isVisible():
            return

        cursor_pos = QCursor.pos()
        global_mouse_pos = self.mapFromGlobal(cursor_pos)

        # 检查鼠标是否在拖动条区域
        drag_bar_rect = self.drag_bar.geometry()
        in_drag_bar = drag_bar_rect.contains(global_mouse_pos)

        # 检查是否在右下角调节区域
        rect = self.rect()
        resize_rect = QRect(
            rect.right() - self._resize_handle_size,
            rect.bottom() - self._resize_handle_size,
            self._resize_handle_size,
            self._resize_handle_size
        )
        in_resize_area = resize_rect.contains(global_mouse_pos)

        # 更新鼠标光标
        if in_resize_area and not self._resizing:
            self.setCursor(Qt.SizeFDiagCursor)
        elif not in_resize_area and not self._resizing:
            self.setCursor(Qt.ArrowCursor)

        if in_drag_bar != self._drag_bar_hover:
            self._drag_bar_hover = in_drag_bar
            if in_drag_bar:
                self.drag_bar._mouse_inside = True
                self.drag_bar._update_style()
            else:
                self.drag_bar._mouse_inside = False
                self.drag_bar._update_style()

    def mousePressEvent(self, event):
        """鼠标按下事件 - 处理右下角调节大小"""
        if event.button() == Qt.LeftButton:
            rect = self.rect()
            resize_rect = QRect(
                rect.right() - self._resize_handle_size,
                rect.bottom() - self._resize_handle_size,
                self._resize_handle_size,
                self._resize_handle_size
            )
            if resize_rect.contains(event.pos()):
                self._resizing = True
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """鼠标移动事件 - 处理窗口大小调节"""
        if self._resizing:
            # 计算新的大小
            new_size = self.mapFromGlobal(QCursor.pos())
            new_width = max(self.minimumWidth(), new_size.x())
            new_height = max(self.minimumHeight(), new_size.y())
            self.resize(new_width, new_height)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.LeftButton:
            self._resizing = False
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _on_hide_clicked(self):
        self.hide()

    def _on_font_down_clicked(self):
        try:
            idx = self.sizes.index(self._font_size)
            if idx > 0:
                new_size = self.sizes[idx - 1]
            else:
                new_size = self.sizes[0]
        except ValueError:
            new_size = 16

        self._font_size = new_size
        self.config.set("ui.font_size", new_size)
        self.caption_history.set_font_size(new_size)

    def _on_font_up_clicked(self):
        try:
            idx = self.sizes.index(self._font_size)
            if idx < len(self.sizes) - 1:
                new_size = self.sizes[idx + 1]
            else:
                new_size = self.sizes[-1]
        except ValueError:
            new_size = 16

        self._font_size = new_size
        self.config.set("ui.font_size", new_size)
        self.caption_history.set_font_size(new_size)

    def update_caption(self, text, caption_type="answer"):
        self.caption_history.add_caption(text, caption_type)

    def clear_caption(self):
        self.caption_history.clear()

    def showEvent(self, event):
        super().showEvent(event)
        self.visibilityChanged.emit(True)
        # 重新定位到屏幕底部
        screen = self.screen().geometry()
        overlay_width = self.width()
        overlay_height = self.height()
        x = screen.left() + (screen.width() - overlay_width) // 2
        y = screen.bottom() - overlay_height - 40
        self.move(x, y)

    def hideEvent(self, event):
        super().hideEvent(event)
        self.visibilityChanged.emit(False)

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange:
            self.visibilityChanged.emit(self.isVisible())
        super().changeEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F12:
            if self.isVisible():
                self.hide()
            else:
                self.show()
            event.accept()
            return
        elif event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_Left:
            self.caption_history._show_previous()
            event.accept()
            return
        elif event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_Right:
            self.caption_history._show_next()
            event.accept()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event):
        self._hover_timer.stop()
        super().closeEvent(event)
