import os

from launch.logging import get_logger

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def _build_nodes(context):
    # 启动期日志器，用于输出当前实际加载的地图文件等关键信息。
    logger = get_logger('diablo_odin_mapplanner_launch')
    pkg_share = get_package_share_directory('diablo_odin_mapplanner')

    # 地图选择逻辑：
    # 1) 如果传入 map_yaml（绝对路径），优先使用该文件；
    # 2) 否则退回到包内 maps/<map_file_name>.yaml。
    map_file_name = LaunchConfiguration('map_file_name').perform(context)
    map_yaml_arg = LaunchConfiguration('map_yaml').perform(context).strip()
    if map_yaml_arg:
        map_yaml = map_yaml_arg
    else:
        map_yaml = os.path.join(pkg_share, 'maps', f'{map_file_name}.yaml')

    # 启动前做文件存在性检查，避免 map_server 在生命周期配置阶段才报错。
    if not os.path.isfile(map_yaml):
        raise RuntimeError(f'Map yaml not found: {map_yaml}')

    logger.info(f'Using map yaml: {map_yaml}')

    map_topic = LaunchConfiguration('map_topic')
    goal_topic = LaunchConfiguration('goal_topic')
    path_topic = LaunchConfiguration('path_topic')
    service_name = LaunchConfiguration('service_name')
    inflation_radius = LaunchConfiguration('inflation_radius')
    inflated_map_topic = LaunchConfiguration('inflated_map_topic')
    publish_path = LaunchConfiguration('publish_path')
    arrive_topic = LaunchConfiguration('arrive_topic')
    goal_tolerance = LaunchConfiguration('goal_tolerance')

    # 地图服务节点：从 yaml 读取静态地图并发布 OccupancyGrid。
    map_server_node = Node(
        package='nav2_map_server',
        executable='map_server',
        name='map_server',
        output='screen',
        parameters=[{'yaml_filename': map_yaml}],
        remappings=[('/map', map_topic)],
    )

    # 生命周期管理器：负责将 map_server 从 unconfigured/configuring 驱动到 active。
    map_server_lifecycle = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_map_server',
        output='screen',
        parameters=[{
            'autostart': True,
            'node_names': ['map_server'],
        }],
    )

    # 全局规划节点：
    # 订阅地图和目标点，执行 A*，发布全局路径与膨胀地图，并提供重规划服务。
    map_planner_node = Node(
        package='diablo_odin_mapplanner',
        executable='map_planner_node',
        name='map_planner',
        output='screen',
        parameters=[{
            'inflation_radius': inflation_radius,
            'service_name': service_name,
            'publish_path': publish_path,
            'map_frame': 'map',
            'base_frame': 'odin1_base_link',
        }],
        remappings=[
            ('map', map_topic),
            ('/move_base_simple/goal', goal_topic),
            ('initial_path', path_topic),
            ('inflated_map', inflated_map_topic),
        ],
    )

    # 目标状态机：收到 arrive 事件后，判断是否到达目标；未到达则调用规划服务重规划。
    goal_state_machine_node = Node(
        package='diablo_odin_mapplanner',
        executable='goal_state_machine_node',
        name='goal_state_machine',
        output='screen',
        parameters=[{
            'plan_service': service_name,
            'goal_tolerance': goal_tolerance,
            'map_frame': 'map',
            'base_frame': 'odin1_base_link',
        }],
        remappings=[
            ('/neupan/arrive', arrive_topic),
            ('/move_base_simple/goal', goal_topic),
        ],
    )

    # 固定外参：机器人底盘到雷达的静态 TF。
    static_tf_node = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='odin1_to_lidar',
        arguments=['0.00347', '0.03447', '0.02174', '0', '0', '0', '1', 'odin1_base_link', 'odin1_lidar_link'],
        output='screen',
    )

    # 点云转激光：把 /odin1/cloud_slam 转成 /scan，供下游基于 LaserScan 的模块使用。
    pc_to_scan_node = Node(
        package='pointcloud_to_laserscan',
        executable='pointcloud_to_laserscan_node',
        name='pc_to_scan',
        output='screen',
        parameters=[{
            'target_frame': 'odin1_base_link',
            'transform_tolerance': 0.1,
            'min_height': 0.0,
            'max_height': 0.3,
            'angle_min': -0.7853,
            'angle_max': 0.7853,
            'angle_increment': 0.017,
            'scan_time': 0.1,
            'range_min': 0.2,
            'range_max': 5.0,
            'use_inf': True,
            'inf_epsilon': 1.0,
        }],
        remappings=[
            ('cloud_in', '/odin1/cloud_slam'),
            ('scan', '/scan'),
        ],
    )

    # 返回要启动的全部节点。
    return [
        map_server_node,
        map_server_lifecycle,
        map_planner_node,
        goal_state_machine_node,
        static_tf_node,
        pc_to_scan_node,
    ]


def generate_launch_description():
    # 统一声明 launch 参数，便于命令行覆盖：
    # - map_yaml: 绝对路径地图 yaml（优先）
    # - map_file_name: 包内地图名（不带 .yaml）
    # - map_topic/path_topic/service_name 等：接口命名与行为调节
    return LaunchDescription([
        DeclareLaunchArgument('map_topic', default_value='/map'),
        DeclareLaunchArgument('map_yaml', default_value=''),
        # 这里修改地图名称
        DeclareLaunchArgument('map_file_name', default_value='officemap'),
        DeclareLaunchArgument('goal_topic', default_value='/move_base_simple/goal'),
        DeclareLaunchArgument('path_topic', default_value='/initial_path'),
        DeclareLaunchArgument('service_name', default_value='/map_planner/plan'),
        DeclareLaunchArgument('inflation_radius', default_value='0.25'),
        DeclareLaunchArgument('inflated_map_topic', default_value='/inflated_map'),
        DeclareLaunchArgument('publish_path', default_value='true'),
        DeclareLaunchArgument('arrive_topic', default_value='/neupan/arrive'),
        DeclareLaunchArgument('goal_tolerance', default_value='0.6'),
        OpaqueFunction(function=lambda context: _build_nodes(context)),
    ])
