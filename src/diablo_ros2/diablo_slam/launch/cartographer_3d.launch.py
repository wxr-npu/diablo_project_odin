from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, SetRemap
from launch_ros.substitutions import FindPackageShare
from launch.launch_description_sources import PythonLaunchDescriptionSource
import os

def generate_launch_description():

    ## ***** Launch arguments *****
    use_sim_time_arg = DeclareLaunchArgument('use_sim_time', default_value = 'False')

    cartographer_node = Node(
        package = 'cartographer_ros',
        executable = 'cartographer_node',
        parameters = [{'use_sim_time': LaunchConfiguration('use_sim_time')}],
        arguments = [
            '-configuration_directory', FindPackageShare('diablo_slam').find('diablo_slam') + '/config',
            '-configuration_basename', 'backpack_3d.lua'],
        remappings = [
            ('odom', '/odom'),
            ('imu', '/livox/imu'),
            ('points2', '/livox/lidar'),
            # ('points2_1', 'horizontal_laser_3d'),
            # ('points2_2', 'vertical_laser_3d')
            ],
        output = 'screen'
        )

    cartographer_occupancy_grid_node = Node(
        package = 'cartographer_ros',
        executable = 'cartographer_occupancy_grid_node',
        parameters = [
            {'use_sim_time': True},
            {'resolution': 0.05}],
        )

    rviz_node=Node(
        package = 'rviz2',
        namespace = 'rviz2',
        executable = 'rviz2',
        name = 'rviz2',
        output = 'screen' ,
        arguments = ['-d', FindPackageShare('cartographer_ros').find('cartographer_ros') + '/configuration_files/demo_3d.rviz']
        )

    return LaunchDescription([
        use_sim_time_arg,
        rviz_node,
        cartographer_node,
        cartographer_occupancy_grid_node,
    ])
