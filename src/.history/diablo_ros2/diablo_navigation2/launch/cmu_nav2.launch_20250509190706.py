# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import os
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, TextSubstitution
from launch_ros.actions import Node
from launch_ros.descriptions import ParameterFile
from nav2_common.launch import RewrittenYaml


def generate_launch_description():
    # Get the launch directory
    bringup_dir = get_package_share_directory("diablo_bringup")
    launch_dir = os.path.join(bringup_dir, "launch")
    nav2_dir = os.path.join(get_package_share_directory('diablo_navigation2'))
    nav2_launch_file_dir = os.path.join(get_package_share_directory('nav2_bringup'),'launch')
    rviz_config_dir = os.path.join(get_package_share_directory('nav2_bringup'),'rviz','nav2_default_view.rviz')

    map_share_dir = os.path.join(get_package_share_directory('diablo_navigation2'), 'maps')
    path = Path(map_share_dir)
    map_src_dir =  Path(path.parents[4], "src/diablo_ros2", *path.parts[-2:])

    # Create the launch configuration variables
    namespace = LaunchConfiguration("namespace")
    slam = LaunchConfiguration("slam")
    use_sim_time = LaunchConfiguration('use_sim_time', default='false')
    use_map = LaunchConfiguration('use_map_yaml', default='tianbotoffice_602')
    params_file = LaunchConfiguration("params_file")

    # https://answers.ros.org/question/358655/ros2-concatenate-string-to-launchargument/
    map_dir = LaunchConfiguration(
        'map',
        default = [map_src_dir,
            '/',
            use_map,
            '.yaml']
    )
    param_dir = LaunchConfiguration(
        'params_file',
        default = [nav2_dir,'/params','/cmu_nav2.yaml']
    )

    configured_params = ParameterFile(
        RewrittenYaml(
            source_file=params_file,
            root_key=namespace,
            param_rewrites={},
            convert_types=True,
        ),
        allow_substs=True,
    )

    # Declare the launch arguments
    declare_namespace_cmd = DeclareLaunchArgument(
        "namespace",
        default_value="hcx",
        description="Top-level namespace",
    )

    declare_slam_cmd = DeclareLaunchArgument(
        "slam",
        default_value="False",
        description="Whether run a SLAM. If True, it will disable small_gicp and send static tf (map->odom)",
    )

    declare_use_sim_time_cmd = DeclareLaunchArgument(
        "use_sim_time",
        default_value="False",
        description="Whether use sim time",
    )

    declare_map_yaml_cmd = DeclareLaunchArgument(
        "use_map_yaml",
        default_value=map_dir,
        description="Full path to map file to load",
    )

    declare_params_file_cmd = DeclareLaunchArgument(
        "params_file",
        default_value=param_dir,
        description="Full path to param file to load",
    )

    rviz_cmd = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config_dir],
        output='screen'
    )

    loam_interface_cmd = Node(
        package="loam_interface",
        executable="loam_interface_node",
        name="loam_interface",
        output="screen",
        # respawn=use_respawn,
        respawn_delay=2.0,
        parameters=[configured_params],
        # arguments=["--ros-args", "--log-level", log_level],
    )

    sensor_scan_generation_cmd = Node(
        package="sensor_scan_generation",
        executable="sensor_scan_generation_node",
        name="sensor_scan_generation",
        output="screen",
        # respawn=use_respawn,
        respawn_delay=2.0,
        parameters=[configured_params],
        # arguments=["--ros-args", "--log-level", log_level],
    )

    terrain_analysis_cmd = Node(
        package="terrain_analysis",
        executable="terrainAnalysis",
        name="terrain_analysis",
        output="screen",
        # respawn=use_respawn,
        respawn_delay=2.0,
        # arguments=["--ros-args", "--log-level", log_level],
        parameters=[configured_params],
    )

    terrain_analysis_ext_cmd = Node(
        package="terrain_analysis_ext",
        executable="terrainAnalysisExt",
        name="terrain_analysis_ext",
        output="screen",
        # respawn=use_respawn,
        respawn_delay=2.0,
        # arguments=["--ros-args", "--log-level", log_level],
        parameters=[configured_params],
    )

    bringup_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(launch_dir, "diablo_bringup.launch.py")),
    )

    cmu_nav2_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(nav2_launch_file_dir, "bringup_launch.py")),
        launch_arguments = {
            'map':map_dir,
            'use_sim_time':use_sim_time,
            'params_file':param_dir
        }.items(),
    )

    ld = LaunchDescription()

    # Declare the launch options
    ld.add_action(declare_namespace_cmd)
    ld.add_action(declare_slam_cmd)
    ld.add_action(declare_map_yaml_cmd)
    ld.add_action(declare_use_sim_time_cmd)
    ld.add_action(declare_params_file_cmd)

    # Add the actions to launch all of the navigation nodes
    ld.add_action(bringup_cmd)
    ld.add_action(loam_interface_cmd)
    ld.add_action(sensor_scan_generation_cmd)
    ld.add_action(terrain_analysis_cmd)
    ld.add_action(terrain_analysis_ext_cmd)
    ld.add_action(cmu_nav2_cmd)
    ld.add_action(rviz_cmd)

    return ld
