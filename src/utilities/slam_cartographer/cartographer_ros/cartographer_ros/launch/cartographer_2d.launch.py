from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

# my_robot_2d.launch.py
def generate_launch_description():

    ## ***** Launch arguments *****
    use_sim_time_arg = DeclareLaunchArgument('use_sim_time', default_value = 'False')

    ## ***** File paths ******
    pkg_share = FindPackageShare('cartographer_ros').find('cartographer_ros')
    '''
    去掉了urdf以及robot_state_publisher_node
    '''
    # 修改为my_robot_2d.lua 文件 以及 激光雷达话题remapping(一个激光雷达的话，映射为scan即可；多个激光雷达需要映射为scan1、scan2...)
    cartographer_node = Node(
        package = 'cartographer_ros',
        executable = 'cartographer_node',
        parameters = [{'use_sim_time': LaunchConfiguration('use_sim_time')}],
        arguments = [
            '-configuration_directory', FindPackageShare('cartographer_ros').find('cartographer_ros') + '/configuration_files',
            '-configuration_basename', 'my_robot_2d.lua'],
        remappings = [
            ('scan', '/sick_lms_1xx/scan')],
        output = 'screen'
        )

    cartographer_occupancy_grid_node = Node(
        package = 'cartographer_ros',
        executable = 'cartographer_occupancy_grid_node',
        parameters = [
            {'use_sim_time': True},
            {'resolution': 0.05}],
        )

    return LaunchDescription([
        use_sim_time_arg,
        # Nodes
        # robot_state_publisher_node, 注释了这个node
        cartographer_node,
        cartographer_occupancy_grid_node,
    ])
