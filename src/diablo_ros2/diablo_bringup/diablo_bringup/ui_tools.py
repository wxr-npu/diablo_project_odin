#!/usr/bin/env python3

import tkinter as tk
import subprocess
import threading
from tkinter import ttk  # 导入 ttk 模块以使用现代风格的控件
import math
import time

def run_command(command, button):
    """
    在单独的线程中执行命令，并更新按钮状态。

    Args:
        command (str): 要执行的命令。
        button (ttk.Button): 要更新的按钮对象。
    """
    def _run():
        button.config(state=tk.DISABLED)  # 禁用按钮
        button.configure(style="Disabled.TButton") # 使用禁用的样式
        try:
            subprocess.run(command, shell=True, check=True)
        except subprocess.CalledProcessError as e:
            print(f"命令执行失败: {e}")  # 打印错误信息
        except Exception as e:
            print(f"发生错误: {e}")
        finally:
            button.config(state=tk.NORMAL)  # 重新启用按钮
            button.configure(style="TButton") # 恢复按钮样式

    threading.Thread(target=_run).start()  # 在新线程中执行 _run 函数

def execute_stand():
    run_command("ros2 topic pub /stand std_msgs/msg/String '{data: standup}' --once", stand_button)

def execute_sitdown():
    run_command("ros2 topic pub /stand std_msgs/msg/String '{data: sitdown}' --once", sitdown_button)

def execute_led_on():
    run_command("ros2 topic pub /led std_msgs/msg/String '{data: 0 255 0 0}' --once", led_on_button)

def execute_led_off():
    run_command("ros2 topic pub /led std_msgs/msg/String '{data: 0 0 0 0}' --once", led_off_button)

def execute_turtle_command(pos_x, pos_y, yaw, turtle_button):
    """执行 turtle 命令，并替换参数。"""
    command = f"ros2 topic pub /cmd_vel geometry_msgs/msg/Twist \"{{linear: {{x: {pos_x}, y: {pos_y}, z: 0.0}}, angular: {{x: 0.0, y: 0.0, z: {yaw}}}}}\" --once"
    run_command(command, turtle_button)
    time.sleep(0.5)
    stop_command = f"ros2 topic pub /cmd_vel geometry_msgs/msg/Twist \"{{linear: {{x: 0.0, y: 0.0, z: 0.0}}, angular: {{x: 0.0, y: 0.0, z: 0.0}}}}\" --once"
    run_command(stop_command, turtle_button)

# 创建主窗口
window = tk.Tk()
window.title("HCX UI Control")
window.geometry("360x420")  # 适当增加窗口高度

# 使用 ttk 创建具有现代外观的按钮
style = ttk.Style()
style.configure("TButton",
                padding=10,
                font=("Arial", 12),
                background="#4AB1E1",  # 浅蓝色
                foreground="white",
                borderwidth=0,
                relief="raised")
style.map("TButton",
          foreground=[('disabled', 'gray'), ('active', 'white')],
          background=[('disabled', 'lightgray'),
                      ('active', '#66BB6A'),  # 稍微亮一点的绿色
                      ('pressed', '#388E3C')]  # 深绿色
          )
style.configure("Disabled.TButton",
                padding=10,
                font=("Arial", 12),
                background="lightgray",  # 灰色
                foreground="gray",
                borderwidth=0,
                relief="flat")

# 创建按钮
stand_button = ttk.Button(window, text="站起", command=execute_stand, style="TButton")
stand_button.pack(pady=10, padx=20, fill=tk.X)

sitdown_button = ttk.Button(window, text="蹲下", command=execute_sitdown, style="TButton")
sitdown_button.pack(pady=10, padx=20, fill=tk.X)

led_on_button = ttk.Button(window, text="开启探照灯", command=execute_led_on, style="TButton")
led_on_button.pack(pady=10, padx=20, fill=tk.X)

led_off_button = ttk.Button(window, text="关闭探照灯", command=execute_led_off, style="TButton")
led_off_button.pack(pady=10, padx=20, fill=tk.X)

# 创建方向控制按钮
frame = tk.Frame(window)
frame.pack()

up_button = ttk.Button(frame, text="⬆️", style="TButton")
up_button.grid(row=0, column=1, padx=5, pady=5)
down_button = ttk.Button(frame, text="⬇️", style="TButton")
down_button.grid(row=2, column=1, padx=5, pady=5)
left_button = ttk.Button(frame, text="⬅️", style="TButton")
left_button.grid(row=1, column=0, padx=5, pady=5)
right_button = ttk.Button(frame, text="➡️", style="TButton")
right_button.grid(row=1, column=2, padx=5, pady=5)
stop_button = ttk.Button(frame, text="O", style="TButton")
stop_button.grid(row=1, column=1, padx=5, pady=5)

def move_turtle(direction):
    """移动乌龟并执行相应的命令"""
    if direction == "up":
        execute_turtle_command(0.5, 0.0, 0.0, up_button)  # 前进
    elif direction == "down":
        execute_turtle_command(-0.5, 0.0, 0.0, down_button) # 后退
    elif direction == "left":
        execute_turtle_command(0.0, 0.0, 0.5, left_button)  # 左转
    elif direction == "right":
        execute_turtle_command(0.0, -0.0,-0.5, right_button) # 右转
    elif direction == "stop":
        execute_turtle_command(0.0, 0, 0.0, stop_button) # 停止

up_button.config(command=lambda: move_turtle("up"))
down_button.config(command=lambda: move_turtle("down"))
left_button.config(command=lambda: move_turtle("left"))
right_button.config(command=lambda: move_turtle("right"))
stop_button.config(command=lambda: move_turtle("stop"))

# 运行主循环
window.mainloop()
