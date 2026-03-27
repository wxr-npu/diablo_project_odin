#!/usr/bin/env/ python3

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo
from launch.substitutions import LaunchConfiguration,TextSubstitution
from launch_ros.actions import Node

def generate_launch_description():
    """Generate a launch description for 3 single diablo mqtt driver."""

    # Serial port and baud rate for LED driver
    mqtt_server_ip_arg = DeclareLaunchArgument(
        'mqtt_server_ip',
        default_value=TextSubstitution(text="192.168.50.240")  # mqtt server ip
    )
    mqtt_robot_name_arg = DeclareLaunchArgument(
        'mqtt_robot_name',
        default_value=TextSubstitution(text="hcx01")       # mqtt topic robot name
    )

    mqtt_receive_node = Node(
        package='diablo_mqtt',
        executable='mqtt_receive',
        output='screen',
        parameters=[{'mqtt_server_ip': LaunchConfiguration('mqtt_server_ip'),
                     'mqtt_robot_name': LaunchConfiguration('mqtt_robot_name'),
            }]
        )
    mqtt_send_node = Node(
        package='diablo_mqtt',
        executable='mqtt_send',
        output='screen',
        parameters=[{'mqtt_robot_name': LaunchConfiguration('mqtt_robot_name'),
            }]
        )

    return LaunchDescription([
        mqtt_server_ip_arg,
        mqtt_robot_name_arg,
        mqtt_receive_node, 
        mqtt_send_node
    ])
