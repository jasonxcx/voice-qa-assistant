"""测试 pynput 全局键盘监听"""
import sys
import time

try:
    from pynput import keyboard
    from pynput.keyboard import Key, KeyCode
    print("[OK] pynput 导入成功")
except ImportError as e:
    print(f"[ERROR] pynput 导入失败：{e}")
    sys.exit(1)

# 记录 Ctrl 键状态
ctrl_pressed = False

def on_press(key):
    global ctrl_pressed
    try:
        print(f"按键按下：{key}, type={type(key).__name__}")
        
        # 检测 Ctrl 键
        if key in (keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
            ctrl_pressed = True
            print("→ Ctrl 键按下")
            return
        
        if not ctrl_pressed:
            return
        
        # 检测 F5-F9
        if isinstance(key, KeyCode):
            key_name = None
            if hasattr(key, 'vk') and key.vk:
                print(f"→ vk={key.vk}")
                if key.vk == 115: key_name = 'F4'
                elif key.vk == 116: key_name = 'F5'
                elif key.vk == 117: key_name = 'F6'
                elif key.vk == 118: key_name = 'F7'
                elif key.vk == 119: key_name = 'F8'
                elif key.vk == 120: key_name = 'F9'
            
            if key_name:
                print(f"★★★ 触发快捷键：Ctrl+{key_name} ★★★")
                
    except Exception as e:
        print(f"错误：{e}")

def on_release(key):
    global ctrl_pressed
    try:
        if key in (keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
            ctrl_pressed = False
            print("← Ctrl 键释放")
    except Exception as e:
        print(f"错误：{e}")

# 启动监听器
print("\n=== pynput 键盘监听测试 ===")
print("按 Ctrl+F4~F9 测试快捷键")
print("按 Esc 退出测试\n")

listener = keyboard.Listener(on_press=on_press, on_release=on_release)
listener.start()
print("[OK] 监听器已启动")

# 保持运行
try:
    while True:
        time.sleep(0.1)
except KeyboardInterrupt:
    print("\n测试结束")
    listener.stop()
