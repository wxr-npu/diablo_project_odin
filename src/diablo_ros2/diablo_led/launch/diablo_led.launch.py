from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo
from launch.substitutions import LaunchConfiguration,TextSubstitution
from launch_ros.actions import Node

def generate_launch_description():
    # Serial port and baud rate for LED driver
    serial_port_arg = DeclareLaunchArgument(
        'serial_port',
        default_value=TextSubstitution(text="/dev/tianbot_led")
    )
    baud_rate_arg = DeclareLaunchArgument(
        'baud_rate',
        default_value=TextSubstitution(text="115200")
    )

    led_node = Node(
            package='diablo_led',
            executable='diablo_led',
            name='led_listener',
            output='log',
            parameters=[{'serial_port': LaunchConfiguration('serial_port'),
                         'baud_rate': LaunchConfiguration('baud_rate'),
                       }]
    )

    return LaunchDescription([
        serial_port_arg,
        baud_rate_arg,
        led_node,
        LogInfo(msg=['Running diablo_led node'])
    ])