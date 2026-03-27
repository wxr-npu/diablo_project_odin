from launch_ros.actions import Node
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
import os
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    share_dir = get_package_share_directory('diablo_rviz')

    rviz_config_file = os.path.join(share_dir, 'rviz', 'slam.rviz')
    rviz_arg = DeclareLaunchArgument(name='rvizconfig', default_value=str(rviz_config_file),
                                     description='Absolute path to rviz config file')

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config_file],
        output='screen'
    )

    return LaunchDescription([
        rviz_arg,
        rviz_node
    ])
