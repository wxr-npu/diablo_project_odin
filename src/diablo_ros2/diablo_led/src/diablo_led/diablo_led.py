#!/usr/bin/env python

import rclpy
from rclpy.node import Node
from std_msgs.msg import ColorRGBA, Int16MultiArray, String
import serial

class LEDDriverNode(Node):
    def __init__(self):
        super().__init__('led_driver_node')
        # 获取串口参数，并创建串口对象
        self.declare_parameter('serial_port', value='/dev/tianbot_led')
        self.declare_parameter('baud_rate', value=115200)
        self.serial_port = self.get_parameter('serial_port').value
        self.baud_rate = self.get_parameter('baud_rate').value
        
        # Default serial port
        self.serial_handle = serial.Serial(self.serial_port, self.baud_rate)

        if (self.serial_handle):
            self.get_logger().info(f"Connected to serial port: {self.serial_port }")
        else:
            self.get_logger().error(f"Could not connect to serial port: {self.serial_port}")

        # the Initial State of led
        self.send_color_command(1, 44, 200, 80)
        self.send_color_command(2, 44, 200, 80) 
        self.send_color_command(3, 44, 200, 80)

        # 订阅 illumination_led_color 主题，并创建回调函数
        self.illumination_led_sub = self.create_subscription(ColorRGBA, 'illumination_led_color', self.illumination_led_callback, 10)
        # 订阅 left_led_color 主题，并创建回调函数
        self.left_led_sub = self.create_subscription(ColorRGBA, 'left_led_color', self.left_led_callback, 10)
        # 订阅 middle_led_color 主题，并创建回调函数
        self.middle_led_sub = self.create_subscription(ColorRGBA, 'middle_led_color', self.middle_led_callback, 10)
        # 订阅 right_led_color 主题，并创建回调函数
        self.right_led_sub = self.create_subscription(ColorRGBA, 'right_led_color', self.right_led_callback, 10)
        # 订阅 led 话题，创建回调函数
        self.led_sub = self.create_subscription(String, 'led', self.led_callback, 10)

    def send_color_command(self, group, red, green, blue):
        # 创建命令字节数组，并发送到串口
        command = bytearray([0xA5, group, red, green, blue, 0x5A])
        self.serial_handle.write(command)
        self.get_logger().info(f"Sent command to {self.serial_port} : {command}")

    def led_callback(self, led_data):
        '''
             |---|---|
           / ^   ^   ^ \
          ^             ^
          0  1   2   3  0
        '''

        self.get_logger().info(f"Led data: {led_data.data}")
        data = led_data.data.split()
        led_num = int(data[0])
        rgb_data = [int(color_data) for color_data in data[1:]]
        
        # eliminate Anomalous rgb_data Data
        rgb_data = [min(max(color_data, 0), 255) for color_data in rgb_data]
        self.get_logger().info(f"rgb_data: {rgb_data}")

        # eliminate Anomalous led_num Data
        if led_num < 4:
            if led_num == 0:
                self.send_color_command(0, rgb_data[0], rgb_data[0], rgb_data[0])
            else :
                self.send_color_command(led_num, rgb_data[0], rgb_data[1], rgb_data[2])     # r,g,b 
        else:
            self.get_logger().warning("Invalid data, please check you led_data!")
        
        # 只运行一次
        return None

    def illumination_led_callback(self, data):
        # 将 data 中的 r、g、b 值转换为 0-255 范围的值
        illumination_value = int(data.r * 255)  # 转换为 0-255 范围的值
        # 调用 send_color_command 函数，发送命令
        self.send_color_command(0, illumination_value, illumination_value, illumination_value)
        self.get_logger().info(f"Illumination LED: {illumination_value}")

    def left_led_callback(self, data):
        # 调用 send_color_command 函数，发送命令
        self.send_color_command(3, int(data.r), int(data.g), int(data.b))

    def middle_led_callback(self, data):
        # 调用 send_color_command 函数，发送命令
        self.send_color_command(2, int(data.r), int(data.g), int(data.b))

    def right_led_callback(self, data):
        # 调用 send_color_command 函数，发送命令
        self.send_color_command(1, int(data.r), int(data.g), int(data.b))

def main(args=None):
    rclpy.init(args=args)
    node = LEDDriverNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()