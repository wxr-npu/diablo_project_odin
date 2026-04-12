import os
from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    # 包路径与资源路径
    nav2_dir = os.path.join(get_package_share_directory('diablo_navigation2'))
    map_share_dir = os.path.join(get_package_share_directory('diablo_navigation2'), 'maps')
    path = Path(map_share_dir)
    # 从 install/share/... 回推到 src/...，用于默认地图文件路径
    map_src_dir =  Path(path.parents[4], "src/diablo_ros2", *path.parts[-2:])
    nav2_launch_file_dir = os.path.join(get_package_share_directory('nav2_bringup'),'launch')
    rviz_config_dir = os.path.join(get_package_share_directory('nav2_bringup'),'rviz','nav2_default_view.rviz')

    # 可通过命令行覆盖的 Launch 参数
    use_sim_time = LaunchConfiguration('use_sim_time', default='false')
    use_map = LaunchConfiguration('use_map', default='tianbotoffice_602')

    # https://answers.ros.org/question/358655/ros2-concatenate-string-to-launchargument/
    # 地图文件默认拼接为: <map_src_dir>/<use_map>.yaml
    map_dir = LaunchConfiguration(
        'map',
        default = [map_src_dir,
            '/',
            use_map,
            '.yaml']
    )
    # Nav2 参数文件
    param_dir = LaunchConfiguration(
        'params_file',
        default = [nav2_dir,'/params','/diablo_nav2.yaml']
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument('use_sim_time',default_value=use_sim_time,description='Use simulation (Gazebo) clock if true'),
            DeclareLaunchArgument('map',default_value = map_dir,description = 'Full path to map file to load'),
            DeclareLaunchArgument('params_file',default_value = param_dir,description = 'Full path to param file to load'),
            
            # 启动 Nav2 主流程（由 bringup_launch.py 决定具体节点）
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource([nav2_launch_file_dir,'/bringup_launch.py']),
                launch_arguments = {
                    'map':map_dir,
                    'use_sim_time':use_sim_time,
                    'params_file':param_dir
                }.items(),
            ),
            
            # IncludeLaunchDescription(
            #     PythonLaunchDescriptionSource([nav2_dir,'/launch','/diablo_state_publisher.launch.py'])
            # ),

            # 启动 RViz，加载 Nav2 默认可视化配置
            Node(
                package = 'rviz2',
                executable = 'rviz2',
                arguments = ['-d',rviz_config_dir],
                output = 'screen'
                )
        ])
