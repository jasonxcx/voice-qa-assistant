"""
UI 样式表
"""

# 字幕窗口样式
OVERLAY_STYLESHEET = """
QWidget#overlayWindow {{
    background-color: rgba(0, 0, 0, 102);  /* rgba(0,0,0,0.4) = 102/255 */
    border-radius: 12px;
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

# 主窗口样式
MAIN_WINDOW_STYLESHEET = """
QMainWindow {{
    background-color: #1E1E1E;
}}

QWidget#centralWidget {{
    background-color: #1E1E1E;
}}

QLabel#titleLabel {{
    color: #FFFFFF;
    font-size: 24px;
    font-weight: bold;
    padding: 10px;
}}

QLabel#statusLabel {{
    color: #9AA0A6;
    font-size: 14px;
    padding: 5px;
}}

QPushButton {{
    background-color: #0078D4;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 10px 24px;
    font-size: 14px;
    font-weight: 500;
}}

QPushButton:hover {{
    background-color: #1084D8;
}}

QPushButton:pressed {{
    background-color: #006CBE;
}}

QPushButton:disabled {{
    background-color: #3C3C3C;
    color: #666666;
}}

QGroupBox {{
    color: #FFFFFF;
    font-size: 14px;
    font-weight: 500;
    border: 1px solid #3C3C3C;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 10px;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 8px;
    color: #9AA0A6;
}}

QLineEdit {{
    background-color: #2D2D2D;
    color: #FFFFFF;
    border: 1px solid #3C3C3C;
    border-radius: 4px;
    padding: 8px 12px;
    font-size: 13px;
}}

QLineEdit:focus {{
    border: 1px solid #0078D4;
}}

QComboBox {{
    background-color: #2D2D2D;
    color: #FFFFFF;
    border: 1px solid #3C3C3C;
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
    border-top: 5px solid #9AA0A6;
    margin-right: 8px;
}}

QComboBox QAbstractItemView {{
    background-color: #2D2D2D;
    color: #FFFFFF;
    border: 1px solid #3C3C3C;
    selection-background-color: #0078D4;
}}

QCheckBox {{
    color: #FFFFFF;
    font-size: 13px;
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 1px solid #3C3C3C;
    border-radius: 4px;
    background-color: #2D2D2D;
}}

QCheckBox::indicator:checked {{
    background-color: #0078D4;
    image: url(checkbox_checked.png);
}}
"""

# 状态颜色
STATUS_COLORS = {
    "idle": "#9AA0A6",      # 灰色 - 空闲
    "listening": "#4CAF50",  # 绿色 - 监听中
    "transcribing": "#2196F3",  # 蓝色 - 转写中
    "generating": "#FF9800",  # 橙色 - 生成中
    "error": "#F44336",      # 红色 - 错误
}
