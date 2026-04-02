import os

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import IncludeLaunchDescription
from launch.substitutions import LaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    # 各功能包 launch 目录
    livox_dir = os.path.join(get_package_share_directory('livox_ros_driver2'),'launch_ROS2')
    realsense2_cam_dir = os.path.join(get_package_share_directory('diablo_bringup'),'launch')
    nmea_dir = os.path.join(get_package_share_directory('nmea_navsat_driver'), 'launch')
    mqtt_dir = os.path.join(get_package_share_directory('diablo_mqtt'),'launch')
    led_dir = os.path.join(get_package_share_directory('diablo_led'),'launch')
    diablo_ctrl_dir = os.path.join(get_package_share_directory('diablo_bringup'),'launch')
    diablo_tf_dir = os.path.join(get_package_share_directory('diablo_description'),'launch')
    
    return LaunchDescription(
        [
            # 1) 传感器驱动：Livox 激光雷达
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource([livox_dir,'/msg_MID360_launch.py'])
            ),

            # 2) 传感器驱动：RealSense 相机
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource([realsense2_cam_dir,'/rs_camera.launch.py'])
            ),
            # IncludeLaunchDescription(
            #     PythonLaunchDescriptionSource([nmea_dir,'/nmea_serial_driver.launch.py'])
            # ),
                
            # 3) 远程通信：MQTT 收发
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource([mqtt_dir,'/diablo_mqtt.launch.py'])
            ),

            # 4) 外设控制：氛围灯
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource([led_dir,'/diablo_led.launch.py'])
            ),

            # 5) 机器人控制：底盘控制 + 站立控制 + 简易 UI
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource([diablo_ctrl_dir,'/diablo_ctrl.launch.py'])
            ),

            # 6) 坐标系：机器人静态/动态 TF
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource([diablo_tf_dir,'/diablo_tf.launch.py'])
            ),

            # 7) 状态估计：融合轮速里程计与 IMU 输出 /odom
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

            # 8) 感知转换：将 Livox 点云投影为 2D LaserScan 供导航/建图使用
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

            # 9) 控制消息转换：融合 cmd_vel 与键盘控制消息
            Node(
                package = 'diablo_convert',
                executable = 'msg_convert_node',
                output = 'screen'
            ),

            # 10) 里程计发布：基于电机状态计算轮式里程计
            Node(
                package = 'diablo_odom',
                executable = 'odom_publish_node',
                output = 'screen'
            ),
        ]
    )