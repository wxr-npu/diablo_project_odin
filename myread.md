# 关闭不必要的传感器
ros2 launch diablo_bringup diablo_bringup.launch.py 
## diablo_bringup.launch.py
配置CYCLONEDDS_URI，提高自动参与者索引上限
### 机器人控制：底盘控制 + 站立控制 + 简易 UI
启动三个节点
diablo_ctrl_node
diablo_stand_node
user_interface_node

#### diablo_ctrl_node
底盘核心控制节点，负责真正和机器人底层控制器通信。


发布
/diablo_ctrl_node
  Subscribers:
    /diablo/MotionCmd: motion_msgs/msg/MotionCtrl

  Publishers:
    /diablo/sensor/Battery: sensor_msgs/msg/BatteryState
    /diablo/sensor/Body_state: motion_msgs/msg/RobotStatus
    /diablo/sensor/Imu: sensor_msgs/msg/Imu
    /diablo/sensor/ImuEuler: ception_msgs/msg/IMUEuler
    /diablo/sensor/Motors: motion_msgs/msg/LegMotors


- 将高层控制指令转换为底盘 SDK 命令并下发
- 发布机器人传感器信息

#### diablo_stand_node
站立/蹲下指令转换节点，负责把简单字符串命令转换为机器人姿态控制消息。

/diablo_stand_node
  Subscribers:
    /stand: std_msgs/msg/String
  Publishers:
    /key_control: motion_msgs/msg/MotionCtrl

功能：
- 订阅 `/stand` 接收 `standup` 和 `sitdown` 指令
- 生成 `MotionCtrl` 消息并发布到 `/key_control`
- 通过组合姿态、升降、站立模式等字段实现机器人站起或蹲下

它本身不直接控制底盘，而是把人类可读命令转换成底层可执行控制消息。

#### user_interface_node---UI界面
简易图形界面节点，提供桌面按钮控制。
不在node当中显示
在 diablo_ctrl.launch.py 里，user_interface_node 只是把可执行文件 ui_tools.py 当作进程拉起。
ui_tools.py 里没有 rclpy.init、没有 Node、没有 create_publisher。它是 Tkinter 程序，通过 subprocess 调 ros2 topic pub 发消息。
ros2 node list 只显示已经注册到 ROS 图里的节点。纯 GUI 进程不会显示。


### 控制消息转换：融合 cmd_vel 与键盘控制消息
msg_convert//ros类当中写的是msg_convert

/msg_convert
  Subscribers:
    /cmd_vel: geometry_msgs/msg/Twist               # 导航来的控制指令
    /key_control: motion_msgs/msg/MotionCtrl        # 

  Publishers:
    /diablo/MotionCmd: motion_msgs/msg/MotionCtrl   # 最终控制消息



### odin驱动节点---host_sdk_sample








# odin基础移植

## node
/diablo_ctrl_node
/diablo_stand_node
/ekf_filter_node
/host_sdk_sample
/joint_state_publisher
/msg_convert
/odom_publish_node
/robot_state_publisher
/rviz2
/static_transform_publisher
/static_transform_publisher
/static_transform_publisher
/static_transform_publisher
/transform_listener_impl_55eb59af73a0
/transform_listener_impl_55fc51584460



## topic
/clicked_point
/cmd_vel
/diablo/MotionCmd
/diablo/sensor/Battery
/diablo/sensor/Body_state
/diablo/sensor/Imu
/diablo/sensor/ImuEuler
/diablo/sensor/Motors
/diablo_odom
/diagnostics
/goal_pose
/initialpose
/joint_states
/key_control
/odin1/camera_pose_visual
/odin1/cloud_raw
/odin1/cloud_render
/odin1/cloud_slam
/odin1/image
/odin1/image/compressed
/odin1/image/intensity_gray
/odin1/image/undistorted
/odin1/imu
/odin1/odometry
/odin1/odometry_highfreq
/odin1/path
/odom
/parameter_events
/robot_description
/rosout
/set_pose
/stand
/tf
/tf_static


# SLAM建图
这里直接使用odin内置的闭源SLAM方法
1. 编辑 odin_ros_driver/config/control_command.yaml
   - custom_map_mode: 1
2. 启动终端1（diablo_bringup_odin）
3. 执行建图脚本
```bash
bash src/diablo_perception/odin_ros_driver/script/map_recording_ros2.sh mapname
```

产物：
- PCD：src/diablo_perception/odin_ros_driver/odin_map/pcd/
3D点云文件Point Cloud Data
- BIN：src/diablo_perception/odin_ros_driver/odin_map/
用于Odin加载地图时使用的二进制文件
- PGM/YAML：src/diablo_ros2/diablo_navigation2/maps/odin_maps/
2D导航使用的地图



# 导航----重点
因为odin内部关键节点闭源，所以得自制节点
1. AMCL：odin内置

## 全局规划器与其他节点

```bash
ros2 launch diablo_odin_mapplanner whole.launch.py
```
1. map_server_node - `nav2`官方节点
 - 地图服务节点：从 yaml 读取静态地图并发布 OccupancyGrid。

2. map_server_lifecycle - `nav2`官方节点
 - 生命周期管理器：负责将 map_server 从 unconfigured/configuring 驱动到 active。

3. map_planner_node
 - 订阅地图和目标点，执行 A*，发布全局路径与膨胀地图，并提供重规划服务
 - 自制节点 `src/diablo_ros2/diablo_odin_mapplanner/src/map_planner.cpp`
4. goal_state_machine_node
 - 目标状态机：收到 arrive 事件后，判断是否到达目标；未到达则调用规划服务重规划。
 - 自制节点 `src/diablo_ros2/diablo_odin_mapplanner/src/goal_state_machine.cpp`

5. static_tf_node
 - 静态 TF
6. pc_to_scan_node - 官方节点
 - pointcloud_to_laserscan：点云转scan


## 局部规划器----neupan
```bash
python /home/tianbot/diablo_ws/src/diablo_ros2/diablo_neupan/diablo_neupan/neupan_ros2.py
```









