import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import String
from sensor_msgs.msg import BatteryState, NavSatFix

class MqttSendNode(Node):
    def __init__(self):
        super().__init__('mqtt_to_ros_node')
        subscriber = self.create_subscription(String, 'mqtt_txd', self.mqtt_callback, 10)
        battery_subscriber = self.create_subscription(BatteryState, '/diablo/sensor/Battery', self.battery_callback, 10)
        gps_subscriber = self.create_subscription(NavSatFix, '/fix', self.gps_callback, 10)
        self.stand_pub = self.create_publisher(String, 'stand', 2)
        self.led_pub = self.create_publisher(String, 'led', 2)
        self.cmd_vel_pub = self.create_publisher(Twist, 'cmd_vel', 10)
        self.mqtt_rxd_pub = self.create_publisher(String, '/mqtt_rxd', 10)

    def mqtt_callback(self, msg):
        # 解析收到的消息
        received_data = msg.data.split()  # 假设消息格式为 "setvel 线速度 角速度"
        cmd_type = received_data[0]
        # 假设消息格式为 
        '''
        receive: "setvel linear_velocity angular_velocity" , such as setvel 1.0 0.0
                "setled led_num r g b"              , such as setled 0 255 255 255
                
                |---|---|
            / ^   ^   ^ \
            ^             ^
            0  1   2   3  0

            led_num : 
                0: illumination_led
                1: right_led
                2: middle_led
                3: right_led
        description: prase and convert msgs from mqtt and publish to ROS topic boardcast
        return 
        '''
        # 检查消息格式
    
        if len(received_data) > 5:
            self.get_logger().error("Invalid message format or command length is larger than 5 unit!!!!!")
            return
        else:
            # 处理 set_vel 命令
            if cmd_type == 'setvel':
                try:
                    linear_vel = float(received_data[1])
                    angular_vel = float(received_data[2])
                except ValueError:
                    self.get_logger().warning("Invalid velocity value")
                    return

                # 创建 Twist 消息
                twist_msg = Twist()
                twist_msg.linear.x = linear_vel
                twist_msg.angular.z = angular_vel

                # 发布到 cmd_vel 话题
                self.cmd_vel_pub.publish(twist_msg)

            # 处理 set_led 命令
            elif cmd_type == 'setled':
                try:
                    # 灯的序号
                    led_data = String()
                    led_data.data = received_data[1] + ' ' + received_data[2] + ' ' + received_data[3] + ' ' + received_data[4]

                except ValueError:
                    self.get_logger().warning("Invalid LED color value or LED num")
                    return

                # 发布到相应的 LED 话题
                self.led_pub.publish(led_data)

            elif cmd_type == 'setpose':
                try:
                    # True
                    stand_data = String()
                    if received_data[1] == '1':
                        stand_data.data = 'standup'
                    elif received_data[1] == '0':
                        stand_data.data = 'sitdown'
                    else:
                        stand_data.data = ''

                except ValueError:
                    self.get_logger().warning("Invalid LED color value or LED num")
                    return

                # 发布到相应的 POSE 话题
                self.stand_pub.publish(stand_data)
            else:
                self.get_logger().warning("Invalid command, please check mqtt publisher")
        

    def battery_callback(self, msg):
        # 获取电池电压信息
        battery_voltage = msg.voltage
        mqtt_msg = String()

        # 构建发送给 mqtt_rxd 话题的消息
        mqtt_msg.data = "BATT " + str(round(battery_voltage, 3))

        # 发布到 mqtt_rxd 话题
        self.mqtt_rxd_pub.publish(mqtt_msg)

    def gps_callback(self, msg):
        # 获取 GPS 位置信息
        latitude = msg.latitude
        longitude = msg.longitude

        mqtt_msg = String()
        # 构建发送给 mqtt_rxd 话题的消息
        mqtt_msg.data = "GPS {} {}".format(longitude, latitude)

        # 发布到 mqtt_rxd 话题
        self.mqtt_rxd_pub.publish(mqtt_msg)

    def led_callback(self, msg):
        # 获取 LED 状态信息
        led_data = msg.data.split()
        led_num = led_data[0]
        led_state = int(led_data[1]) + int(led_data[2]) + int(led_data[3])

        mqtt_msg = String()
        # 构建发送给 mqtt_rxd 话题的消息
        mqtt_msg.data = "LED {} {}".format(led_num, led_state)

        # 发布到 mqtt_rxd 话题
        self.mqtt_rxd_pub.publish(mqtt_msg)

    def bodystate_callback(self, msg):
        # 获取 GPS 位置信息
        latitude = msg.latitude
        longitude = msg.longitude

        mqtt_msg = String()
        # 构建发送给 mqtt_rxd 话题的消息
        mqtt_msg.data = "GPS {} {}".format(longitude, latitude)

        # 发布到 mqtt_rxd 话题
        self.mqtt_rxd_pub.publish(mqtt_msg)

def main(args=None):
    rclpy.init(args=args)
    mqtt_to_ros_publisher = MqttSendNode()
    rclpy.spin(mqtt_to_ros_publisher)
    rclpy.shutdown()

if __name__ == '__main__':
    main()