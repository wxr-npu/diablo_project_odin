import rclpy
from rclpy.node import Node
from std_msgs.msg import String

class LedPublisher(Node):
    def __init__(self):
        super().__init__('led_publisher')
        self.publisher_ = self.create_publisher(String, 'led', 10)
        timer_period = 1.0  # seconds
        self.timer = self.create_timer(timer_period, self.timer_callback)
        self.led_data = [
            "0 255 0 0",
            "1 0 0 255",
            "2 0 255 0",
            "3 0 0 255",
            "0 0 0 0",
            "1 0 0 0",
            "2 0 0 0",
            "3 0 0 0",
        ]
        self.i = 0

    def timer_callback(self):
        msg = String()
        msg.data = self.led_data[self.i]
        self.publisher_.publish(msg)
        self.get_logger().info('Publishing: "%s"' % msg.data)
        self.i = (self.i + 1) % len(self.led_data)

def main(args=None):
    rclpy.init(args=args)
    led_publisher = LedPublisher()
    rclpy.spin(led_publisher)
    led_publisher.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()