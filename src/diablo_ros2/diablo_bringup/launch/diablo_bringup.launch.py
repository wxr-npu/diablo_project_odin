import os

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import IncludeLaunchDescription
from launch.substitutions import LaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    livox_dir = os.path.join(get_package_share_directory('livox_ros_driver2'),'launch_ROS2')
    realsense2_cam_dir = os.path.join(get_package_share_directory('diablo_bringup'),'launch')
    nmea_dir = os.path.join(get_package_share_directory('nmea_navsat_driver'), 'launch')
    mqtt_dir = os.path.join(get_package_share_directory('diablo_mqtt'),'launch')
    led_dir = os.path.join(get_package_share_directory('diablo_led'),'launch')
    diablo_ctrl_dir = os.path.join(get_package_share_directory('diablo_bringup'),'launch')
    diablo_tf_dir = os.path.join(get_package_share_directory('diablo_description'),'launch')
    
    return LaunchDescription(
        [
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource([livox_dir,'/msg_MID360_launch.py'])
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource([realsense2_cam_dir,'/rs_camera.launch.py'])
            ),
            # IncludeLaunchDescription(
            #     PythonLaunchDescriptionSource([nmea_dir,'/nmea_serial_driver.launch.py'])
            # ),
                
            # mqtt
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource([mqtt_dir,'/diablo_mqtt.launch.py'])
            ),

            # led
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource([led_dir,'/diablo_led.launch.py'])
            ),

            # diablo_ctrl
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource([diablo_ctrl_dir,'/diablo_ctrl.launch.py'])
            ),

            # diablo_tf
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource([diablo_tf_dir,'/diablo_tf.launch.py'])
            ),

            # robot_localization
            Node(
                package='robot_localization',
                executable='ekf_node',
                name='ekf_filter_node',
                output='screen',
                parameters=[os.path.join(get_package_share_directory("diablo_bringup"), 'config', 'diablo_ekf.yaml')],
                remappings=[
                    ('/odometry/filtered', '/odom'),
                ],
            ),

            # pointcloud_to_laserscan
            Node(
                package='pointcloud_to_laserscan', 
                executable='pointcloud_to_laserscan_node',
                name='pointcloud_to_laserscan',
                remappings=[
                    # ('cloud_in', '/livox/lidar'),
                    ('cloud_in', '/livox/lidar/pointcloud'),
                ],
                parameters=[{
                    'target_frame': 'livox_frame',
                    'transform_tolerance': 0.01,
                    'min_height': 0.0,
                    'max_height': 0.1,
                    'angle_min': -3.1415,  # -M_PI/2
                    'angle_max': 3.1415,  # M_PI/2
                    'angle_increment': 0.005,  # M_PI/360.0
                    'scan_time': 0.1,
                    'range_min': 0.1,
                    'range_max': 30.0,
                    'use_inf': True,
                    'inf_epsilon': 1.0
                }],
            ),
            Node(
                package = 'diablo_convert',
                executable = 'msg_convert_node',
                output = 'screen'
            ),
            Node(
                package = 'diablo_odom',
                executable = 'odom_publish_node',
                output = 'screen'
            ),
        ]
    )