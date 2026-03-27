import launch
import launch_ros.actions
from launch.substitutions import PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, TextSubstitution

def generate_launch_description():
    rviz_cfg = PathJoinSubstitution(
        [FindPackageShare("localizer"), "rviz", "localizer.rviz"]
    )
    localizer_config_path = PathJoinSubstitution(
        [FindPackageShare("localizer"), "config", "localizer.yaml"]
    )

    lio_config_path = PathJoinSubstitution(
        [FindPackageShare("fastlio2"), "config", "lio.yaml"]
    )
    pcd_file_arg = DeclareLaunchArgument(
        'pcd_file',
        default_value=TextSubstitution(text="/home/tianbot/diablo_ws/src/diablo_perception/point_lio/PCD/tianbotoffice-602.pcd")
    )
    return launch.LaunchDescription(
        [
            pcd_file_arg,
            launch_ros.actions.Node(
                package="fastlio2",
                namespace="fastlio2",
                executable="lio_node",
                name="lio_node",
                output="screen",
                parameters=[
                    {"config_path": lio_config_path.perform(launch.LaunchContext())}
                ],
            ),
            launch_ros.actions.Node(
                package="localizer",
                namespace="localizer",
                executable="localizer_node",
                name="localizer_node",
                output="screen",
                parameters=[
                    {
                        "config_path": localizer_config_path.perform(
                            launch.LaunchContext()
                        ),
                        'pcd_file': LaunchConfiguration('pcd_file')
                    }
                ],
            ),
            launch_ros.actions.Node(
                package="localizer",
                namespace="localizer",
                executable="relocalize_client_node",
                name="relocalize_client",
                output="screen",
                parameters=[{
                    'pcd_file': LaunchConfiguration('pcd_file')
                }],
            ),
            #launch_ros.actions.Node(
            #    package="rviz2",
            #    namespace="localizer",
            #    executable="rviz2",
            #    name="rviz2",
            #    output="screen",
            #    arguments=["-d", rviz_cfg.perform(launch.LaunchContext())],
            #)
        ]
    )
