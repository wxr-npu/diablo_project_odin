# ROS2移植软件流程
## 建图逻辑
启动的shell脚本：bash src/diablo_perception/odin_ros_driver/script/map_recording_ros2.sh mapname

1. 调用 pointcloud_saver 的服务：订阅激光 SLAM 点云话题，在收到命令后开始/停止累积点云，最后对点云做降采样和滤波，保存为 PCD 文件。
2. odin_ros_driver/pointcloud_saver_ros2_node
订阅 /odin1/cloud_slam，录制并保存为 *.pcd
3. odin_ros_driver/pcd2pgm_ros2_node
读取 PCD 并发布 /map
4. nav2_map_server/map_saver_cli 
保存 2D 栅格地图（yaml/pgm）
5. 执行 ./set_param.sh save_map 1 触发 Odin 保存 .bin
6. 可选修改 config/control_command.yaml（把 custom_map_mode 改为 2，并写入 relocalization_map_abs_path）


## 导航逻辑
注：局部规划器仍然使用neupan
1. nav2_map_server/map_server
加载地图

2. nav2_lifecycle_manager/lifecycle_manager
管理map_server生命周期


3. pointcloud_to_laserscan/pointcloud_to_laserscan_node
pointcloud点云转laserscan2D点云

4. tf2_ros/static_transform_publisher
发布TF

5. /map_planner_node
进行全局规划
sub：
/map (nav_msgs/msg/OccupancyGrid)
/move_base_simple/goal (geometry_msgs/msg/PoseStamped)（接收RVIZ信号）

pub：
/initial_path (nav_msgs/Path)
/inflated_map (nav_msgs/OccupancyGrid)
/map_planner/result (std_msgs/msg/Bool)


6. /goal_state_machine_node
达到触发重规划
sub:
/neupan/arrive (std_msgs/msg/Empty)
/move_base_simple/goal
pub:
无










