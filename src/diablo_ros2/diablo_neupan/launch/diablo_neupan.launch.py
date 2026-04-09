import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    # 获取 diablo_neupan 安装后的 share 目录。
    # 这样无论源码路径怎么变，默认配置都能正确找到。
    pkg_share = get_package_share_directory('diablo_neupan')
    default_cfg = os.path.join(pkg_share, 'config', 'neupan_config.yaml')

    # LaunchConfiguration 是运行时参数占位符。
    # 真正值由 launch 命令行或默认值决定。
    enable_scan_converter = LaunchConfiguration('enable_scan_converter')
    config_file = LaunchConfiguration('config_file')

    return LaunchDescription([
        # 是否启用点云转 LaserScan。
        # true: 使用 /odin1/cloud_slam 生成 /scan，供 NeuPAN 订阅。
        # false: 假设系统中已经有其他节点在发布 /scan。
        DeclareLaunchArgument(
            'enable_scan_converter',
            default_value='true',
            description='Convert /odin1/cloud_slam to /scan for NeuPAN',
        ),
        # NeuPAN 主配置文件路径。
        # 可通过命令行覆盖，例如:
        # ros2 launch ... config_file:=/abs/path/to/custom.yaml
        DeclareLaunchArgument(
            'config_file',
            default_value=default_cfg,
            description='Absolute path to NeuPAN ROS2 config yaml',
        ),

        # 1) 点云转 2D LaserScan 节点（可选）
        # 只在 enable_scan_converter=true 时启动。
        Node(
            condition=IfCondition(enable_scan_converter),
            package='pointcloud_to_laserscan',
            executable='pointcloud_to_laserscan_node',
            name='neupan_pc_to_scan',
            output='screen',
            remappings=[
                # 输入 Odin 的 SLAM 点云，输出标准 /scan。
                ('cloud_in', '/odin1/cloud_slam'),
                ('scan', '/scan'),
            ],
            parameters=[{
                # 将扫描结果表达在机器人基座坐标系，
                # 方便与导航/控制使用的 base_link 对齐。
                'target_frame': 'odin1_base_link',

                # TF 等待容忍时间（秒），避免轻微时序抖动导致转换失败。
                'transform_tolerance': 0.1,

                # 仅保留该高度区间内的点（单位: 米），用于抑制地面/高处噪点。
                'min_height': 0.0,
                'max_height': 0.3,

                # 前向视场约 [-45°, +45°]，减小无关侧向障碍干扰。
                'angle_min': -0.7853,
                'angle_max': 0.7853,
                'angle_increment': 0.017,

                # 激光扫描时间模型与量程约束。
                'scan_time': 0.1,
                'range_min': 0.2,
                'range_max': 8.0,

                # 无回波用 inf 表示，便于下游算法区分“无障碍”与“无效值”。
                'use_inf': True,
                'inf_epsilon': 1.0,
            }],
        ),

        # 2) NeuPAN ROS2 主节点
        # 将上方 launch 参数 config_file 传给节点内部参数，
        # 对应 neupan_ros2.py 中必须提供的 config_file。
        Node(
            package='diablo_neupan',
            executable='neupan_ros2.py',
            name='neupan_node',
            output='screen',
            parameters=[{
                'config_file': config_file,
            }],
        ),
    ])
