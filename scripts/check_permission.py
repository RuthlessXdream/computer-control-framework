#!/usr/bin/env python3
"""
检查macOS辅助功能权限
"""

import subprocess
import sys

print("=" * 60)
print("     macOS 辅助功能权限检查")
print("=" * 60)

# 检查是否有辅助功能权限
try:
    # 尝试执行一个简单的鼠标操作来测试权限
    import Quartz
    
    # 获取当前鼠标位置
    event = Quartz.CGEventCreate(None)
    pos = Quartz.CGEventGetLocation(event)
    print(f"\n✅ 可以读取鼠标位置: ({int(pos.x)}, {int(pos.y)})")
    
    # 尝试移动鼠标
    print("\n正在测试鼠标控制权限...")
    move_event = Quartz.CGEventCreateMouseEvent(
        None,
        Quartz.kCGEventMouseMoved,
        (pos.x + 10, pos.y + 10),
        Quartz.kCGMouseButtonLeft
    )
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, move_event)
    
    print("✅ 鼠标控制命令已发送")
    print("\n如果你的鼠标没有移动，说明需要授权。")
    
except Exception as e:
    print(f"\n❌ 错误: {e}")

print("\n" + "=" * 60)
print("📋 如何授予权限:")
print("=" * 60)
print("""
1. 打开 系统设置 (System Settings)
2. 点击 隐私与安全性 (Privacy & Security)
3. 点击 辅助功能 (Accessibility)
4. 点击 + 号添加应用
5. 找到并添加 Cursor (或 Terminal)
6. 确保开关是打开状态 ✅

或者用这个命令直接打开设置:
""")

# 打开系统偏好设置
print("正在打开系统设置...")
subprocess.run([
    "open", 
    "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
])

print("\n⚠️  添加权限后，需要重启 Cursor!")
print("=" * 60)

