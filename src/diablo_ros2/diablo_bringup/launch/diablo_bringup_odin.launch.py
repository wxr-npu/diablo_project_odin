import os

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, SetEnvironmentVariable
from launch.substitutions import LaunchConfiguration
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    enable_neupan = LaunchConfiguration('enable_neupan')

    # 各功能包 launch 目录
    livox_dir = os.path.join(get_package_share_directory('livox_ros_driver2'),'launch_ROS2')
    realsense2_cam_dir = os.path.join(get_package_share_directory('diablo_bringup'),'launch')
    nmea_dir = os.path.join(get_package_share_directory('nmea_navsat_driver'), 'launch')
    odin_dir = os.path.join(get_package_share_directory('odin_ros_driver'), 'launch')
    neupan_dir = os.path.join(get_package_share_directory('diablo_neupan'), 'launch')
    mqtt_dir = os.path.join(get_package_share_directory('diablo_mqtt'),'launch')
    led_dir = os.path.join(get_package_share_directory('diablo_led'),'launch')
    diablo_ctrl_dir = os.path.join(get_package_share_directory('diablo_bringup'),'launch')
    diablo_tf_dir = os.path.join(get_package_share_directory('diablo_description'),'launch')
    
    return LaunchDescription(
        [

            # 提高 CycloneDDS 自动参与者索引上限，避免多节点同时启动时域创建失败
            SetEnvironmentVariable(
                name='CYCLONEDDS_URI',
                value='<CycloneDDS><Domain id="any"><Discovery><ParticipantIndex>auto</ParticipantIndex><MaxAutoParticipantIndex>120</MaxAutoParticipantIndex></Discovery></Domain></CycloneDDS>'
            ),

            # odin测试
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource([odin_dir, '/odin1_ros2.launch.py'])
            ),

            # 5) 机器人控制：底盘控制 + 站立控制 + 简易 UI
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource([diablo_ctrl_dir,'/diablo_ctrl.launch.py'])
            ),


            # # 局部规划区neupan
            # IncludeLaunchDescription(
            #     PythonLaunchDescriptionSource([neupan_dir, '/diablo_neupan.launch.py']),
            #     condition=IfCondition(enable_neupan)
            # ),

            # 关闭TF 只保留odin

            # # 8) 感知转换：将 Livox 点云投影为 2D LaserScan 供导航/建图使用
            # Node(
            #     package='pointcloud_to_laserscan', 
            #     executable='pointcloud_to_laserscan_node',
            #     name='pointcloud_to_laserscan',
            #     remappings=[
            #         # ('cloud_in', '/livox/lidar'),
            #         ('cloud_in', '/livox/lidar/pointcloud'),
            #     ],
            #     parameters=[{
            #         'target_frame': 'livox_frame',
            #         'transform_tolerance': 0.01,
            #         'min_height': 0.0,
            #         'max_height': 0.1,
            #         'angle_min': -3.1415,  # -M_PI/2
            #         'angle_max': 3.1415,  # M_PI/2
            #         'angle_increment': 0.005,  # M_PI/360.0
            #         'scan_time': 0.1,
            #         'range_min': 0.1,
            #         'range_max': 30.0,
            #         'use_inf': True,
            #         'inf_epsilon': 1.0
            #     }],
            # ),

            # 9) 控制消息转换：融合 cmd_vel 与键盘控制消息
            Node(
                package = 'diablo_convert',
                executable = 'msg_convert_node',
                output = 'screen'
            ),


        ]
    )