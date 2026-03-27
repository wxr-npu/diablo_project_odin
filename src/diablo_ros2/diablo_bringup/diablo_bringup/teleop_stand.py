#!/usr/bin/env python3

import rclpy
import time
from rclpy.node import Node
from std_msgs.msg import String
from motion_msgs.msg import MotionCtrl

ctrlMsgs = MotionCtrl()

def generMsgs(forward=None, left=None, roll=None, up=None,
                    pitch=None, mode_mark=None, height_ctrl_mode=None,
                    pitch_ctrl_mode=None, roll_ctrl_mode=None, stand_mode=None,
                    jump_mode=False, dance_mode=None, emergency_mode=None):
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
        # print("\rgenerMsg is :\n", end='', flush=True)
        print("\rmode_mark: {0}\t stand_mode: {1}\t up: {2}\n".format(mode_mark, stand_mode, up), end='', flush=True)

class StandListener(Node):

    def __init__(self):
        
        super().__init__('stand_listener_node')
        self.subscription = self.create_subscription(String, 'stand', self.stand_callback, 2)
        self.publisher = self.create_publisher(MotionCtrl, 'key_control', 10)
        self.subscription  # prevent unused variable warning
        self.publisher
    
    def __del__(self):
        self.get_logger().info('Stand Listener Node has been terminated')
        pass

    def stand_callback(self, msg):
        if msg.data == 'standup':
            generMsgs(mode_mark=True, jump_mode=False, stand_mode=True)
            # print("\rmode mark is True\n", end='', flush=True)
            self.publisher.publish(ctrlMsgs)
            time.sleep(1.0)

            generMsgs(mode_mark=False, height_ctrl_mode=True, up=1.0)
            # print("\rmode mark is False\n", end='', flush=True)
            # print("\rheight is set 1.0\n", end='', flush=True)
            self.publisher.publish(ctrlMsgs)

            self.get_logger().warning("Stand up Command has published")

        elif msg.data == 'sitdown':
            generMsgs(mode_mark=False, height_ctrl_mode=True, up=0.5)
            # print("\rheight is set 0.5\n", end='', flush=True)
            self.publisher.publish(ctrlMsgs)
            time.sleep(1.0)

            generMsgs(mode_mark=False, height_ctrl_mode=True, up=-0.5)
            # print("\rheight is set 0.0\n", end='', flush=True)
            self.publisher.publish(ctrlMsgs)
            time.sleep(2.0)

            generMsgs(mode_mark=True, stand_mode=False)
            # print("\rmode mark is True\n", end='', flush=True)
            self.publisher.publish(ctrlMsgs)
            time.sleep(1.0)

            generMsgs(mode_mark=False)
            #print("\rmode_mark is False\n", end='', flush=True)
        
            self.publisher.publish(ctrlMsgs)
            self.get_logger().warning("Sit down Command has published")

        else:
            ctrlMsgs.mode_mark = False
            ctrlMsgs.mode.split_mode = False
            ctrlMsgs.value.forward = 0.0
            ctrlMsgs.value.left = 0.0
            self.get_logger().info("Keep Static Command has published")

            self.publisher.publish(ctrlMsgs)

def main(args=None):
    rclpy.init(args=args)
    stand_node = StandListener()
    rclpy.spin(stand_node)

    # Destroy the node explicitly
    stand_node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
