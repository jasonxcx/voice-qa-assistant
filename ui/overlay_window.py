"""
透明字幕窗口 - 带控制按钮和拖动条
特性：
- 背景完全透明
- 顶部拖动条（可拖动窗口，双击隐藏）
- 控制按钮：隐藏、字体变大、字体变小、监听控制
- F12 全局快捷键显示/隐藏
- 鼠标拖动边缘调节窗口大小
- 显示"等待音频输入..."占位符
"""
from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QScrollArea,
    QGraphicsDropShadowEffect, QSizeGrip
)
from PyQt5.QtCore import Qt, QPoint, QTimer, pyqtSignal, QEvent, QPropertyAnimation, QEasingCurve, QRect
from PyQt5.QtGui import QFont, QColor, QCursor
from collections import deque

try:
    from pynput import keyboard
    HAS_PYNPUT = True
except ImportError:
    keyboard = None
    HAS_PYNPUT = False


class CaptionHistory(QWidget):
    """字幕历史记录组件 - 每个问题占一页"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pages = []  # 每个元素是 {"question": str, "answer": str}
        self.current_page = -1
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
        self.content_label = QLabel(self._placeholder_text)
        self.content_label.setObjectName("contentLabel")
        self.content_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.content_label.setWordWrap(True)
        self.content_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.content_label.setMinimumHeight(60)
        self._set_placeholder_style()
        self._update_font()
        layout.addWidget(self.content_label, 1)

        # 翻页控制已移动到 OverlayWindow - 只保留按钮引用
        self.prev_btn = QPushButton("◀")
        self.prev_btn.setToolTip("上一页")
        self.prev_btn.clicked.connect(self._show_previous)
        self.prev_btn.setFixedSize(32, 32)
        self.prev_btn.setStyleSheet(self._button_stylesheet())

        self.page_label = QLabel("0 / 0")
        self.page_label.setStyleSheet("color: rgba(255, 255, 255, 153); font-size: 11px;")
        self.page_label.setAlignment(Qt.AlignCenter)
        self.page_label.setFixedHeight(32)

        self.next_btn = QPushButton("▶")
        self.next_btn.setToolTip("下一页")
        self.next_btn.clicked.connect(self._show_next)
        self.next_btn.setFixedSize(32, 32)
        self.next_btn.setStyleSheet(self._button_stylesheet())

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

    def add_new_question(self, question: str):
        """添加新问题 - 开始新的一页"""
        self.pages = [p for p in self.pages if p.get("question", "")]
        self.current_page = len(self.pages) - 1

        self.pages.append({"question": question, "answer": ""})
        self.current_page = len(self.pages) - 1
        self._display_current()
        self._update_buttons()

    def update_answer_streaming(self, answer_text: str, page_index: int = None):
        """流式更新回答 - 更新当前页的回答"""
        target_page = page_index if page_index is not None else self.current_page
        if target_page < 0 or target_page >= len(self.pages):
            print(f"[DEBUG] update_answer_streaming: target_page out of range", flush=True)
            return
        self.pages[target_page]["answer"] = answer_text
        self._display_current()

    def add_caption(self, text, caption_type="answer"):
        """添加字幕（向后兼容）"""
        # 对于 listening 类型，使用当前页回答部分来显示（流式更新）
        if caption_type == "listening":
            # listening 类型用于流式更新，更新当前页的回答
            if self.current_page < 0 or self.current_page >= len(self.pages):
                # 如果还没有页面，创建一个临时页面
                self.pages.append({"question": "", "answer": text})
                self.current_page = 0
            else:
                # 更新当前页的回答（覆盖而不是追加）
                self.pages[self.current_page]["answer"] = text
            self._display_current()
        elif caption_type == "answer" or caption_type == "normal":
            # answer/normal 类型追加到回答
            if self.current_page < 0 or self.current_page >= len(self.pages):
                # 如果还没有页面，创建一个
                self.pages.append({"question": "", "answer": text})
                self.current_page = 0
            else:
                # 更新当前页的回答
                current_answer = self.pages[self.current_page]["answer"]
                self.pages[self.current_page]["answer"] = current_answer + text
            self._display_current()
        elif caption_type == "error":
            # 错误类型，添加为新页面的问题部分
            self.pages.append({"question": f"错误：{text}", "answer": ""})
            self.current_page = len(self.pages) - 1
            self._display_current()
            self._update_buttons()

    def update_last_answer(self, new_text: str):
        """更新最后一个 answer 条目（用于流式更新）"""
        self.update_answer_streaming(new_text)

    def _display_current(self):
        """显示当前页的内容"""
        if self.current_page < 0 or self.current_page >= len(self.pages):
            self.content_label.setText(self._placeholder_text)
            self._set_placeholder_style()
            self.page_label.setText("0 / 0")
            return

        page = self.pages[self.current_page]
        question = page.get("question", "")
        answer = page.get("answer", "")

        if not question and not answer:
            self.content_label.setText(self._placeholder_text)
            self._set_placeholder_style()
            self.page_label.setText(f"{self.current_page + 1} / {len(self.pages)}")
            return

        # 组合显示：问题在第一行，回答在后面
        parts = []
        if question:
            # 问题用蓝色显示
            parts.append(f'<span style="color: #90CAF9; font-weight: bold;">问题：{question}</span>')
        if answer:
            # 回答用绿色显示
            parts.append(f'<span style="color: #81C784;">回答：{answer}</span>')

        html = "<br/><br/>".join(parts)
        self.content_label.setText(html)
        self._set_content_style()
        self.page_label.setText(f"{self.current_page + 1} / {len(self.pages)}")

    def _show_previous(self):
        if self.current_page > 0:
            self.current_page -= 1
            self._display_current()
            self._update_buttons()

    def _show_next(self):
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            self._display_current()
            self._update_buttons()

    def _update_buttons(self):
        self.prev_btn.setEnabled(self.current_page > 0)
        self.next_btn.setEnabled(self.current_page < len(self.pages) - 1)

    def clear(self):
        self.pages.clear()
        self.current_page = -1
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
    # 监听控制信号
    listeningStarted = pyqtSignal()
    listeningStopped = pyqtSignal()
    transcriptionModeChanged = pyqtSignal(bool)  # True=手动, False=自动
    sizes = [8, 12, 16, 20, 24, 28, 32, 36, 40]

    def __init__(self, config):
        super().__init__()
        self.config = config
        self._font_size = config.font_size
        self._resizing = False
        self._resize_from_corner = None  # 记录从哪个角调节
        self._resize_start_pos = QPoint()  # 调节开始时的鼠标位置
        self._resize_start_geometry = (0, 0, 0, 0)  # (x, y, width, height)
        self._listening = False  # 监听状态
        self._manual_transcription_mode = bool(self.config.get("ui.transcription.manual_mode", True))
        self._hotkey_listener = None
        self._init_ui()
        self._setup_window_flags()
        self._setup_global_hotkey()
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
        # 初始完全透明
        content_widget.setStyleSheet("""
            QWidget#contentWidget {
                background-color: transparent;
                border: 1px solid transparent;
                border-bottom-left-radius: 12px;
                border-bottom-right-radius: 12px;
            }
        """)

        # 保存 content_widget 引用以便后续修改样式
        self.content_widget = content_widget

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

        self.mode_btn = QPushButton()
        self.mode_btn.setToolTip("切换手动/自动转录模式")
        self.mode_btn.setFixedHeight(28)
        self.mode_btn.clicked.connect(self._on_mode_toggled)
        self.mode_btn.setStyleSheet(self._action_button_stylesheet())

        # 监听控制按钮（合并开始/停止为一个按钮）
        self.listen_btn = QPushButton("▶ 开始监听")
        self.listen_btn.setToolTip("开始/停止监听音频")
        self.listen_btn.setFixedHeight(28)
        self.listen_btn.clicked.connect(self._on_listen_toggled)
        self.listen_btn.setStyleSheet(self._listen_button_stylesheet())
        self.listen_btn.setEnabled(False)  # 初始禁用，等待模型加载完成

        # 添加大小调节提示标签
        self.resize_label = QLabel("⇙ 或 ⇘ 拖动调节大小")
        self.resize_label.setAlignment(Qt.AlignCenter)
        self.resize_label.setStyleSheet("color: rgba(255, 255, 255, 102); font-size: 10px;")
        self.resize_label.setAttribute(Qt.WA_TransparentForMouseEvents)

        button_layout.addWidget(self.hide_btn)
        button_layout.addWidget(self.font_down_btn)
        button_layout.addWidget(self.font_up_btn)
        button_layout.addWidget(self.mode_btn)
        button_layout.addWidget(self.listen_btn)
        button_layout.addWidget(self.resize_label)
        button_layout.addStretch()

        # 翻页按钮放在右下角
        button_layout.addWidget(self.caption_history.prev_btn)
        button_layout.addWidget(self.caption_history.page_label)
        button_layout.addWidget(self.caption_history.next_btn)

        content_layout.addLayout(button_layout)
        main_layout.addWidget(content_widget)

        # 为 content_widget 安装事件过滤器，用于检测 resize 区域
        content_widget.installEventFilter(self)

        # 阴影效果
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 128))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)
        self._apply_transcription_mode_ui()

    def _hide_button_stylesheet(self):
        """隐藏按钮样式 - 灰色"""
        return """
            QPushButton {
                background-color: rgba(128, 128, 128, 100);
                color: #FFFFFF;
                border: none;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(128, 128, 128, 150);
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

    def _listen_button_stylesheet(self):
        """监听按钮样式 - 绿色（未监听）/ 红色（监听中）"""
        # 检查当前状态
        is_listening = getattr(self, '_listening', False)

        if is_listening:
            return """
                QPushButton {
                    background-color: rgba(244, 67, 54, 150);
                    color: #FFFFFF;
                    border: none;
                    border-radius: 4px;
                    padding: 4px 10px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: rgba(244, 67, 54, 200);
                }
                QPushButton:disabled {
                    background-color: rgba(244, 67, 54, 50);
                    color: rgba(255, 255, 255, 100);
                }
            """
        else:
            return """
                QPushButton {
                    background-color: rgba(76, 175, 80, 150);
                    color: #FFFFFF;
                    border: none;
                    border-radius: 4px;
                    padding: 4px 10px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: rgba(76, 175, 80, 200);
                }
                QPushButton:disabled {
                    background-color: rgba(76, 175, 80, 50);
                    color: rgba(255, 255, 255, 100);
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
    
    def _setup_global_hotkey(self):
        """设置全局键盘快捷键 - pynput 方案"""
        if not HAS_PYNPUT or keyboard is None:
            print("[OverlayWindow] pynput 未安装，使用局部 F12 快捷键", flush=True)
            return
        
        try:
            def on_press(key):
                try:
                    if key == keyboard.Key.f12:
                        self._toggle_visibility()
                except AttributeError:
                    pass
                    
            self._hotkey_listener = keyboard.Listener(on_press=on_press)
            self._hotkey_listener.start()
            print("[OverlayWindow] F12 全局热键已注册 (pynput)", flush=True)
        except Exception as e:
            print(f"[OverlayWindow] 全局热键注册失败：{e}", flush=True)
    
    def _toggle_visibility(self):
        """切换窗口可见性（全局热键回调）"""
        if self.isVisible():
            self.hide()
        else:
            self.show()

    def _on_drag_bar_double_click(self):
        """拖动条双击"""
        self.hide()

    def _check_hover_state(self):
        """检测鼠标悬停状态"""
        if not self.isVisible():
            return

        cursor_pos = QCursor.pos()
        global_mouse_pos = self.mapFromGlobal(cursor_pos)

        rect = self.rect()

        # 检查是否在左下角调节区域（增大调节区域到 40 像素）
        bottom_left_rect = QRect(rect.left(), rect.bottom() - 20, 20, 20)
        in_bottom_left = bottom_left_rect.contains(global_mouse_pos)

        # 检查是否在右下角调节区域（增大调节区域到 40 像素）
        bottom_right_rect = QRect(rect.right() - 20, rect.bottom() - 20, 20, 20)
        in_bottom_right = bottom_right_rect.contains(global_mouse_pos)

        # 更新鼠标光标 - 优先显示 resize 光标
        if in_bottom_left:
            self.setCursor(Qt.SizeBDiagCursor)  # ↖ 光标 (左下角)
        elif in_bottom_right:
            self.setCursor(Qt.SizeFDiagCursor)  # ↘ 光标 (右下角)
        else:
            self.setCursor(Qt.ArrowCursor)

    def mousePressEvent(self, event):
        """鼠标按下事件 - 处理直接在窗口上的鼠标事件"""
        if event.button() == Qt.LeftButton:
            rect = self.rect()
            local_mouse_pos = event.pos()

            # 检查左下角区域
            bottom_left_rect = QRect(rect.left(), rect.bottom() - 20, 20, 20)
            if bottom_left_rect.contains(local_mouse_pos):
                self._resizing = True
                self._resize_from_corner = "bottom_left"
                # 记录初始位置和大小，用于计算偏移量
                self._resize_start_pos = event.globalPos()
                self._resize_start_geometry = (self.x(), self.y(), self.width(), self.height())
                event.accept()
                return

            # 检查右下角区域
            bottom_right_rect = QRect(rect.right() - 20, rect.bottom() - 20, 20, 20)
            if bottom_right_rect.contains(local_mouse_pos):
                self._resizing = True
                self._resize_from_corner = "bottom_right"
                # 记录初始位置和大小，用于计算偏移量
                self._resize_start_pos = event.globalPos()
                self._resize_start_geometry = (self.x(), self.y(), self.width(), self.height())
                event.accept()
                return

        # 调用 super() 确保事件正确处理
        super().mousePressEvent(event)

    def eventFilter(self, obj, event):
        """事件过滤器 - 处理 content_widget 的鼠标事件以支持 resize"""
        # 只处理 content_widget 的鼠标按下事件
        if obj == self.content_widget and event.type() == event.MouseButtonPress and event.button() == Qt.LeftButton:
            # 使用全局坐标检测是否在调节区域内
            cursor_global_pos = QCursor.pos()
            window_top_left = self.mapToGlobal(QPoint(0, 0))
            local_mouse_pos = QPoint(
                cursor_global_pos.x() - window_top_left.x(),
                cursor_global_pos.y() - window_top_left.y()
            )
            rect = self.rect()

            # 检查是否在调节区域内
            bottom_left_rect = QRect(rect.left(), rect.bottom() - 20, 20, 20)
            bottom_right_rect = QRect(rect.right() - 20, rect.bottom() - 20, 20, 20)

            if bottom_left_rect.contains(local_mouse_pos) or bottom_right_rect.contains(local_mouse_pos):
                # 在调节区域内，触发窗口的 resize 处理
                self._resize_start_pos = cursor_global_pos
                self._resize_start_geometry = (self.x(), self.y(), self.width(), self.height())

                if bottom_left_rect.contains(local_mouse_pos):
                    self._resizing = True
                    self._resize_from_corner = "bottom_left"
                else:
                    self._resizing = True
                    self._resize_from_corner = "bottom_right"
                return True  # 过滤掉事件，不让 content_widget 处理

        # 不在调节区域内，返回 False 让事件正常传递
        return False

    def mouseMoveEvent(self, event):
        """鼠标移动事件 - 处理窗口大小调节"""
        if self._resizing:
            rect = self.rect()
            cursor_global_pos = QCursor.pos()

            # 计算鼠标移动偏移量
            delta_x = cursor_global_pos.x() - self._resize_start_pos.x()
            delta_y = cursor_global_pos.y() - self._resize_start_pos.y()

            start_x, start_y, start_width, start_height = self._resize_start_geometry

            if self._resize_from_corner == "bottom_left":
                # 左下角调节：固定右上角，鼠标拖动左下角
                # 鼠标向左移动：窗口变宽（右边界固定，左边界左移）
                # 鼠标向右移动：窗口变窄
                # 鼠标向上移动：窗口变矮（上边界固定，下边界上移）
                # 鼠标向下移动：窗口变高

                # 计算新的左边界和宽度
                new_x = start_x + delta_x
                new_width = start_width - delta_x

                # 计算新的高度（上边界固定，下边界随鼠标移动）
                new_height = start_height + delta_y

                # 确保不小于最小尺寸
                if new_width < self.minimumWidth():
                    new_width = self.minimumWidth()
                    new_x = start_x + start_width - new_width

                if new_height < self.minimumHeight():
                    new_height = self.minimumHeight()

                # 应用新的尺寸和位置
                self.setGeometry(new_x, start_y, new_width, new_height)

            elif self._resize_from_corner == "bottom_right":
                # 右下角调节：向左上固定，向右下扩展
                new_width = start_width + delta_x
                new_height = start_height + delta_y

                # 确保不小于最小尺寸
                if new_width < self.minimumWidth():
                    new_width = self.minimumWidth()
                if new_height < self.minimumHeight():
                    new_height = self.minimumHeight()

                self.resize(new_width, new_height)

            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.LeftButton:
            self._resizing = False
            self._resize_from_corner = None
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _on_hide_clicked(self):
        self.hide()

    def set_listen_button_enabled(self, enabled: bool):
        """设置监听按钮的启用状态"""
        print(f"[Debug] set_listen_button_enabled({enabled})", flush=True)
        self.listen_btn.setEnabled(enabled and self._manual_transcription_mode)
        # 重新设置样式以确保样式正确应用
        self.listen_btn.setStyleSheet(self._listen_button_stylesheet())

    def is_manual_transcription_mode(self) -> bool:
        return self._manual_transcription_mode

    def _apply_transcription_mode_ui(self):
        """根据手动/自动模式刷新 UI"""
        if self._manual_transcription_mode:
            self.mode_btn.setText("模式：手动")
            self.listen_btn.setVisible(True)
        else:
            self.mode_btn.setText("模式：自动")
            self.listen_btn.setVisible(False)

    def _on_mode_toggled(self):
        """切换手动/自动转录模式"""
        self._manual_transcription_mode = not self._manual_transcription_mode
        self.config.set("ui.transcription.manual_mode", self._manual_transcription_mode)

        # 从手动切到自动时，先停止手动监听，避免状态残留
        if not self._manual_transcription_mode and self._listening:
            self.listeningStopped.emit()
            self._listening = False
            self.listen_btn.setText("▶ 开始监听")
            self.listen_btn.setStyleSheet(self._listen_button_stylesheet())

        self._apply_transcription_mode_ui()
        self.transcriptionModeChanged.emit(self._manual_transcription_mode)

    def _on_listen_toggled(self):
        """监听按钮切换"""
        if hasattr(self, '_listening') and self._listening:
            # 停止监听
            self.listeningStopped.emit()
            self._listening = False
            self.listen_btn.setText("▶ 开始监听")
            self.listen_btn.setStyleSheet(self._listen_button_stylesheet())
        else:
            # 开始监听
            self.listeningStarted.emit()
            self._listening = True
            self.listen_btn.setText("■ 停止监听")
            self.listen_btn.setProperty("listening", "true")
            self.listen_btn.setStyleSheet(self._listen_button_stylesheet())
            # 开始时立即触发一次转录，捕获用户即将开始的发言
            # 注意：实际的转录会在 _on_overlay_listening_started 中由主窗口处理

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

    def enterEvent(self, event):
        """鼠标移入 - 显示背景色"""
        if hasattr(self, 'content_widget'):
            self.content_widget.setStyleSheet("""
                QWidget#contentWidget {
                    background-color: rgba(30, 30, 30, 200);
                    border: 1px solid rgba(255, 255, 255, 64);
                    border-bottom-left-radius: 12px;
                    border-bottom-right-radius: 12px;
                }
            """)
        super().enterEvent(event)

    def leaveEvent(self, event):
        """鼠标移出 - 恢复透明"""
        if hasattr(self, 'content_widget'):
            self.content_widget.setStyleSheet("""
                QWidget#contentWidget {
                    background-color: transparent;
                    border: 1px solid transparent;
                    border-bottom-left-radius: 12px;
                    border-bottom-right-radius: 12px;
                }
            """)
        super().leaveEvent(event)

    def keyPressEvent(self, event):
        """键盘按键事件 - 保留 Ctrl+Left/Right 用于字幕导航"""
        if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_Left:
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
        # 清理 pynput listener
        if hasattr(self, '_hotkey_listener') and self._hotkey_listener:
            self._hotkey_listener.stop()
        super().closeEvent(event)
