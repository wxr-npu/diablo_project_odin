import os
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    diablo_display_dir = os.path.join(get_package_share_directory('diablo_simulation'),'launch')

    return LaunchDescription(
        [
            # static broadcaster publisher from base_footprint to base_link
            Node(
                package = 'tf2_ros',
                executable = 'static_transform_publisher',
                name='static_transform_publisher',
                arguments=['0', '0', '0', '0', '0', '0', '1', 'base_footprint','base_link']
            ),

            # Transform base_link to diablo_robot 
            Node(
                package='tf2_ros',
                executable='static_transform_publisher',
                name='static_transform_publisher',
                arguments=['0', '0', '0.3', '0', '0', '0', '1', 'base_link', 'diablo_robot']
            ),

            # Transform base_link to lidar_link 
            Node(
                package='tf2_ros',
                executable='static_transform_publisher',
                name='static_transform_publisher',
                arguments=['0', '0', '0.5', '0', '0', '0', '1', 'base_link', 'livox_frame']
            ),

            # Transform base_link to camera_link 
            Node(
                package='tf2_ros',
                executable='static_transform_publisher',
                name='static_transform_publisher',
                arguments=['0', '0', '0.25', '0', '0', '0', '1', 'base_link', 'camera_link']
            ),

            # diablo_description
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource([diablo_display_dir,'/display_no_rviz.launch.py'])
            ),
        ]
    )