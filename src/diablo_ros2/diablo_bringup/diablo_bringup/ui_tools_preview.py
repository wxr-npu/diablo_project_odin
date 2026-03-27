#!/usr/bin/env python3

import tkinter as tk
import subprocess
import threading
from tkinter import ttk  # 导入 ttk 模块以使用现代风格的控件

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

def start_bringup():
    run_command("ros2 topic pub /stand std_msgs/msg/String '{data: standup}' --once", stand_button)

def execute_stand():
    run_command("ros2 topic pub /stand std_msgs/msg/String '{data: standup}' --once", stand_button)

def execute_sitdown():
    run_command("ros2 topic pub /stand std_msgs/msg/String '{data: sitdown}' --once", sitdown_button)

def execute_led_on():
    run_command("ros2 topic pub /led std_msgs/msg/String '{data: 0 255 0 0}' --once", led_on_button)

def execute_led_off():
    run_command("ros2 topic pub /led std_msgs/msg/String '{data: 0 0 0 0}' --once", led_off_button)

# 创建主窗口
window = tk.Tk()
window.title("HCX UI Control")  # 修改窗口标题
window.geometry("300x250")  # 设置窗口初始大小，宽度足够显示标题

# 使用 ttk 创建具有现代外观的按钮
style = ttk.Style()
style.configure("TButton",
                padding=10,
                font=("Arial", 12),
                background="#4CAF50",  # 绿色
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
stand_button.pack(pady=10, padx=20, fill=tk.X)  # 添加 padx 和 fill

sitdown_button = ttk.Button(window, text="蹲下", command=execute_sitdown, style="TButton")
sitdown_button.pack(pady=10, padx=20, fill=tk.X)

led_on_button = ttk.Button(window, text="开启探照灯", command=execute_led_on, style="TButton")
led_on_button.pack(pady=10, padx=20, fill=tk.X)

led_off_button = ttk.Button(window, text="关闭探照灯", command=execute_led_off, style="TButton")
led_off_button.pack(pady=10, padx=20, fill=tk.X)

# 运行主循环
window.mainloop()
