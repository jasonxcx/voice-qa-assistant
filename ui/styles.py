"""
UI 样式表 - PySide6 现代深色主题

颜色系统基于 Indigo 主色调，提供统一的视觉风格。
"""

# ============================================================================
# 颜色常量 (Color Palette)
# ============================================================================

# 背景
BACKGROUND = "#0F0F0F"      # 主背景 (near-black)
SURFACE = "#1A1A1A"         # 卡片/表面 (elevated)
SURFACE_HOVER = "#242424"   # hover 状态
BORDER_SUBTLE = "#2A2A2A"   # 细微边框
BORDER_FOCUS = "#3D3D3D"    # focus 边框

# 文字
TEXT_PRIMARY = "#FFFFFF"
TEXT_SECONDARY = "#8A8A8A"   # 标签、提示
TEXT_MUTED = "#5C5C5C"       # disabled

# 强调色 (Indigo)
ACCENT_PRIMARY = "#6366F1"   # 主按钮、高亮
ACCENT_HOVER = "#818CF8"     # hover 状态
ACCENT_ACTIVE = "#4F46E5"    # pressed 状态

# 状态色
SUCCESS = "#22C55E"          # 绿色
WARNING = "#F59E0B"          # 橙色
ERROR = "#EF4444"            # 红色

# ============================================================================
# 按钮样式 (Button Styles)
# ============================================================================

PRIMARY_BUTTON = """
QPushButton {
    background-color: #6366F1;
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 10px 20px;
    font-size: 14px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #818CF8;
}
QPushButton:pressed {
    background-color: #4F46E5;
}
QPushButton:disabled {
    background-color: #2A2A2A;
    color: #5C5C5C;
}
"""

SECONDARY_BUTTON = """
QPushButton {
    background-color: #1A1A1A;
    color: #FFFFFF;
    border: 1px solid #2A2A2A;
    border-radius: 8px;
    padding: 10px 16px;
    font-size: 14px;
}
QPushButton:hover {
    background-color: #242424;
    border: 1px solid #3D3D3D;
}
QPushButton:pressed {
    background-color: #0F0F0F;
}
"""

DANGER_BUTTON = """
QPushButton {
    background-color: rgba(239, 68, 68, 0.15);
    color: #EF4444;
    border: none;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 12px;
}
QPushButton:hover {
    background-color: rgba(239, 68, 68, 0.25);
}
"""

ICON_BUTTON = """
QPushButton {
    background-color: transparent;
    color: #8A8A8A;
    border: none;
    border-radius: 6px;
    padding: 8px;
}
QPushButton:hover {
    background-color: #242424;
    color: #FFFFFF;
}
"""

# ============================================================================
# 卡片样式 (Card Styles)
# ============================================================================

CARD_CONTAINER = """
QWidget#cardContainer {
    background-color: #1A1A1A;
    border: 1px solid #2A2A2A;
    border-radius: 8px;
    padding: 16px;
}
"""

CARD_HEADER = """
QLabel#cardHeader {
    color: #FFFFFF;
    font-size: 14px;
    font-weight: 500;
    padding-bottom: 8px;
}
"""

# ============================================================================
# Overlay 专用常量 (Overlay Window)
# ============================================================================

OVERLAY_BG_SOLID = "rgba(15, 15, 15, 230)"       # hover 时显示
OVERLAY_BG_TRANSPARENT = "rgba(0, 0, 0, 102)"    # 默认透明
OVERLAY_SHADOW = "rgba(0, 0, 0, 180)"
OVERLAY_CAPTION_QUESTION = "#90CAF9"             # 问题蓝色
OVERLAY_CAPTION_ANSWER = "#81C784"               # 回答绿色
OVERLAY_LISTEN_ACTIVE = "rgba(76, 175, 80, 150)"    # 监听中绿色
OVERLAY_LISTEN_INACTIVE = "rgba(244, 67, 54, 150)"  # 未监听红色

# ============================================================================
# 主窗口样式表 (Main Window StyleSheet)
# ============================================================================

MAIN_WINDOW_STYLESHEET = f"""
QMainWindow {{
    background-color: {BACKGROUND};
}}

QWidget#centralWidget {{
    background-color: {BACKGROUND};
}}

QLabel#titleLabel {{
    color: {TEXT_PRIMARY};
    font-size: 24px;
    font-weight: bold;
    padding: 10px;
}}

QLabel#statusLabel {{
    color: {TEXT_SECONDARY};
    font-size: 14px;
    padding: 5px;
}}

QPushButton {{
    background-color: {ACCENT_PRIMARY};
    color: {TEXT_PRIMARY};
    border: none;
    border-radius: 6px;
    padding: 10px 24px;
    font-size: 14px;
    font-weight: 500;
}}

QPushButton:hover {{
    background-color: {ACCENT_HOVER};
}}

QPushButton:pressed {{
    background-color: {ACCENT_ACTIVE};
}}

QPushButton:disabled {{
    background-color: {BORDER_SUBTLE};
    color: {TEXT_MUTED};
}}

QGroupBox {{
    color: {TEXT_PRIMARY};
    font-size: 14px;
    font-weight: 500;
    border: 1px solid {BORDER_SUBTLE};
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 10px;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 8px;
    color: {TEXT_SECONDARY};
}}

QLineEdit {{
    background-color: {SURFACE};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_SUBTLE};
    border-radius: 4px;
    padding: 8px 12px;
    font-size: 13px;
}}

QLineEdit:focus {{
    border: 1px solid {ACCENT_PRIMARY};
}}

QComboBox {{
    background-color: {SURFACE};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_SUBTLE};
    border-radius: 4px;
    padding: 8px 12px;
    font-size: 13px;
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {TEXT_SECONDARY};
    margin-right: 8px;
}}

QComboBox QAbstractItemView {{
    background-color: {SURFACE};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_SUBTLE};
    selection-background-color: {ACCENT_PRIMARY};
}}

QCheckBox {{
    color: {TEXT_PRIMARY};
    font-size: 13px;
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 1px solid {BORDER_SUBTLE};
    border-radius: 4px;
    background-color: {SURFACE};
}}

QCheckBox::indicator:checked {{
    background-color: {ACCENT_PRIMARY};
    image: url(checkbox_checked.png);
}}

QTabWidget::pane {{
    border: 1px solid {BORDER_SUBTLE};
    border-radius: 8px;
    background-color: {BACKGROUND};
}}

QTabBar::tab {{
    background-color: {SURFACE};
    color: {TEXT_SECONDARY};
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    margin-right: 2px;
}}

QTabBar::tab:selected {{
    background-color: {ACCENT_PRIMARY};
    color: {TEXT_PRIMARY};
}}

QTabBar::tab:hover {{
    background-color: {SURFACE_HOVER};
}}

QSlider::groove:horizontal {{
    background-color: {BORDER_SUBTLE};
    height: 6px;
    border-radius: 3px;
}}

QSlider::handle:horizontal {{
    background-color: {ACCENT_PRIMARY};
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}}

QSlider::handle:horizontal:hover {{
    background-color: {ACCENT_HOVER};
}}

QProgressBar {{
    background-color: {BORDER_SUBTLE};
    border: none;
    border-radius: 4px;
    height: 8px;
}}

QProgressBar::chunk {{
    background-color: {ACCENT_PRIMARY};
    border-radius: 4px;
}}

QScrollArea {{
    background-color: transparent;
    border: none;
}}

QScrollBar:vertical {{
    background-color: {BACKGROUND};
    width: 8px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical {{
    background-color: {BORDER_SUBTLE};
    border-radius: 4px;
    min-height: 20px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {BORDER_FOCUS};
}}
"""

# ============================================================================
# Overlay 样式表 (Overlay Window StyleSheet)
# ============================================================================

OVERLAY_STYLESHEET = """
QWidget#overlayWindow {{
    background-color: rgba(0, 0, 0, 102);
    border-radius: {border_radius}px;
}}

QLabel#captionLabel {{
    color: #FFFFFF;
    font-size: {font_size}px;
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
    font-weight: 400;
    padding: 14px 18px;
    background-color: transparent;
    border: none;
}}
"""

# ============================================================================
# 状态颜色 (Status Colors)
# ============================================================================

STATUS_COLORS = {
    "idle": "#9AA0A6",           # 灰色 - 空闲
    "listening": "#4CAF50",      # 绿色 - 监听中
    "transcribing": "#2196F3",   # 蓝色 - 转写中
    "generating": "#FF9800",     # 橙色 - 生成中
    "error": "#F44336",          # 红色 - 错误
}