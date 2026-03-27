import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import paho.mqtt.client as mqtt
import time
import subprocess

class RosToMqttPublisher(Node):

    def __init__(self):
        super().__init__('ros_to_mqtt_publisher')
        
        # init mqtt server ip
        self.declare_parameter('mqtt_server_ip', value="47.108.xxx.xxx")
        self.declare_parameter('mqtt_robot_name', value="HCX01")

        self.mqtt_server_ip = self.get_parameter('mqtt_server_ip').value
        self.mqtt_robot_name = self.get_parameter('mqtt_robot_name').value

        # ROS 发布者
        self.ros_mqtt_publisher = self.create_publisher(String, 'mqtt_txd', 10)

        # 设置断线重连的标志
        self.reconnecting = False

        # MQTT 连接参数
        self.mqtt_broker = f"{self.mqtt_server_ip}"  # MQTT Broker 地址
        self.mqtt_topic_to_publish = f"{self.mqtt_robot_name}/cmd_txd"  # 要发布消息的主题
        self.mqtt_topic_to_subscribe = f"{self.mqtt_robot_name}/cmd_rxd"  # 要订阅的主题
        self.mqtt_ros_topic = "mqtt_rxd"  # ROS 订阅的主题

        # 创建 MQTT 客户端
        self.mqtt_client = mqtt.Client()

        # 设置回调函数
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.on_disconnect = self.on_disconnect  # 添加断线重连回调

        # 延迟连接尝试
        time.sleep(15)

        # 连接到 MQTT Broker
        self.mqtt_client.connect(self.mqtt_broker, 1883, 60)
        # self.mqtt_client.connect_async(self.mqtt_broker, 1883, 60)

        # ROS 订阅者，用于接收来自 ROS 的消息并转发给 MQTT
        self.create_subscription(String, self.mqtt_ros_topic, self.on_ros_mqtt_message, 10)

        # 保持 MQTT 连接
        self.mqtt_client.loop_start()

    def on_connect(self, client, userdata, flags, rc):
        # 检查网络连接状态
        if not self.is_network_connected():
            # 延迟连接尝试
            time.sleep(5)
            self.mqtt_client.connect(self.mqtt_broker, 1883, 60)
            return
        
        # 网络连接正常，继续执行
        self.get_logger().info("Connected with result code " + str(rc))
        # 订阅来自 MQTT 的消息主题
        client.subscribe(self.mqtt_topic_to_subscribe)
    
    # 在断线时触发尝试重新连接逻辑。当 MQTT 客户端检测到断线时，它将尝试重新连接 MQTT Broker。
    # 如果连接失败，它将等待 5 秒钟后再次尝试连接，直到成功连接为止。

    def on_disconnect(self, client, userdata, rc):
        if not self.reconnecting:
            self.get_logger().warning("Disconnected from MQTT Broker. Attempting to reconnect...")
            self.reconnecting = True
            while True:
                try:
                    self.mqtt_client.reconnect()
                    self.reconnecting = False
                    self.get_logger().info("Reconnected to MQTT Broker.")
                    break
                except:
                    self.get_logger().warning("Failed to reconnect. Retrying in 5 seconds...")
                    time.sleep(5)

    def is_network_connected(self):
        try:
            # 使用 ping 命令检查网络连接
            subprocess.run(["ping", "-c", "1", self.mqtt_broker],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
            return True
        except subprocess.CalledProcessError:
            return False

    def on_message(self, client, userdata, msg):
        message = msg.payload.decode()
        self.get_logger().info("Received MQTT message: " + message)

        # 发布收到的 MQTT 消息到 ROS 话题
        msg = String()
        msg.data = message
        if len(message.split()) > 5:
            # illegal command warning callback to mqtt
            self.mqtt_client.publish(self.mqtt_topic_to_publish, f"illegal << {message} >> over 5 unit, skipped...")
        else:
            self.ros_mqtt_publisher.publish(msg)

    def on_ros_mqtt_message(self, msg):
        message = msg.data
        self.get_logger().info("Received ROS message to publish to MQTT: " + message)

        # 发布 ROS 收到的消息到 MQTT 的主题
        self.mqtt_client.publish(self.mqtt_topic_to_publish, message)

def main(args=None):
    rclpy.init(args=args)
    ros_to_mqtt_publisher = RosToMqttPublisher()
    rclpy.spin(ros_to_mqtt_publisher)
    ros_to_mqtt_publisher.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
