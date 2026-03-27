#!/usr/bin/env python3
from http.client import OK
import rclpy
import time
import sys
import tty
import termios
import threading
from rclpy.node import Node
from motion_msgs.msg import MotionCtrl

print("键盘控制启动")
print("""
!!! 在任何情况下你可以按下数字键 '1' 来激活紧急模式，该模式下只允许接收键盘控制而会屏蔽导航消息，在确保机器人安全后通过数字 '2' 键退出
控制模式操作如下：
- 使用 w a s d 控制机器人的前进后退与旋转
- 使用数字3键激活mode_mark模式(True),当且仅当该模式为True时,以下的按键才生效,使用数字4键关闭(False)。
  - z键:触发stand_mode让机器人站立,注意:在ROS下机器人初次站立会有一个起跳的动作,请保证周围留有足够空间
  - x键:卧倒
  - c键:激活跳跃模式
  - f键:激活跳舞模式
  - g键:关闭跳舞模式
- 当激活站立模式后,使用4键关闭mode_mark模式你可以调整机器人的姿态。
  - u键:调整低头
  - o键:调整抬头
  - i键:恢复原位
  - j键:站立高度最高值 1.0
  - k键:站立高度中间值 0.5
  - l键:站立高度最低值 0.0
  - q键:使机器人左倾 0.1
  - e键:使机器人右倾 0.1 如需调整具体数值请在源码中修改
!!!使用数字键 '0' 退出!!!
""")


keyQueue = []
ctrlMsgs = MotionCtrl()
old_setting = termios.tcgetattr(sys.stdin)

def readchar():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

def getKeyBoard():
    global keyQueue
    while True:
        c = readchar()
        keyQueue.append(c)


t1 =threading.Thread(target=getKeyBoard)
t1.setDaemon(True)
t1.start()


def generMsgs(forward=None,left=None,roll=None,up=None,
                pitch=None,mode_mark = None,height_ctrl_mode = None,
                pitch_ctrl_mode = None,roll_ctrl_mode = None,stand_mode = None,
                jump_mode = False,dance_mode = None,emergency_mode = None):
    global ctrlMsgs
    if mode_mark is not None:
        ctrlMsgs.mode_mark = mode_mark
    ctrlMsgs.mode.jump_mode = jump_mode
    if emergency_mode is not None:
        ctrlMsgs.emergency_mode = emergency_mode

    if dance_mode is not None:
        ctrlMsgs.mode.split_mode = dance_mode
    if forward is not None:
        ctrlMsgs.value.forward = forward
    if left is not None:
        ctrlMsgs.value.left = left
    if pitch is not None:
        ctrlMsgs.value.pitch = pitch
    if roll is not None:
        ctrlMsgs.value.roll = roll
    if up is not None:
        ctrlMsgs.value.up = up
    if height_ctrl_mode is not None:
        ctrlMsgs.mode.height_ctrl_mode = height_ctrl_mode
    if pitch_ctrl_mode is not None:
        ctrlMsgs.mode.pitch_ctrl_mode = pitch_ctrl_mode
    if roll_ctrl_mode is not None:
        ctrlMsgs.mode.roll_ctrl_mode = roll_ctrl_mode
    if stand_mode is not None:
        ctrlMsgs.mode.stand_mode = stand_mode


def main(args=None):
    global ctrlMsgs
    rclpy.init(args=args) 
    node = Node("diablo_teleop_node")

    teleop_cmd = node.create_publisher(MotionCtrl,"key_control",10)

    while True:
        if len(keyQueue) > 0:
            key = keyQueue.pop(0)
            if key == 'w':
                generMsgs(forward=1.0)
            elif key == 's':
                generMsgs(forward=-1.0)
            elif key == 'a':
                generMsgs(left=1.0)
            elif key == 'd':
                generMsgs(left=-1.0)
            elif key == 'e':
                generMsgs(roll=0.1)
            elif key == 'q':
                generMsgs(roll=-0.1)
            elif key == 'r':
                generMsgs(roll=0.0)
            elif key == 'j':
                generMsgs(up = 1.0)
            elif key == 'k':
               generMsgs(up = 0.5)
            elif key == 'l':
               generMsgs(up = 0.0)
                
            elif key == 'u':
                if ctrlMsgs.value.pitch is None:  
                    ctrlMsgs.value.pitch = 0.0     
                else:
                    ctrlMsgs.value.pitch += 0.1 
            elif key == 'i':
                generMsgs(pitch = 0.0)
            elif key == 'o':
                if ctrlMsgs.value.pitch is None:
                    ctrlMsgs.value.pitch = 0.0
                else:
                    ctrlMsgs.value.pitch -= 0.1
            elif key == '1' :
                generMsgs(emergency_mode = True)
                print("\remergency mode is True\n",end='', flush=True)
            elif key == '2' :
                generMsgs(emergency_mode = False)
                print("\remergency mode is False\n",end='',flush=True)
            elif key == '3' :
                generMsgs(mode_mark = True)
                print("\rmode mark is True\n",end='',flush=True)
            elif key == '4' :
                generMsgs(mode_mark = False)
                print("\rmode mark is False\n",end='',flush=True)
            elif key == 'v':
                generMsgs(height_ctrl_mode=True)
            elif key == 'b':
                generMsgs(height_ctrl_mode=False)
            elif key == 'n':
                generMsgs(pitch_ctrl_mode=True)
            elif key == 'm':
                generMsgs(pitch_ctrl_mode=False)

            elif key == 'z':
                generMsgs(stand_mode=True)
            elif key == 'x':
                generMsgs(stand_mode=False)
            elif key == 'c':
                generMsgs(jump_mode=True)
            elif key == 'f':
                generMsgs(dance_mode=True)
            elif key == 'g':
                generMsgs(dance_mode=False)
            elif key == '0':
                print("Exiting loop")
                break
        else:
            ctrlMsgs.value.forward = 0.0
            ctrlMsgs.value.left = 0.0
        teleop_cmd.publish(ctrlMsgs)
        time.sleep(0.04)
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_setting)
    print('exit!')
    rclpy.shutdown() 




