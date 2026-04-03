
# bringup
ros2 launch diablo_bringup diablo_bringup.launch.py 
## diablo_bringup.launch.py

### 1) 传感器驱动：Livox 激光雷达---驱动包
/livox_driver_node
直接读取传感器数据流  不读取话题

### 2) 传感器驱动：RealSense 相机---本工程没有源码
/camera/camera
工程当中没有源码

### 3) 远程通信：MQTT 收发---MQTT
/ros_to_mqtt_publisher
/mqtt_to_ros_node

#### /ros_to_mqtt_publisher
  Subscribers:

  Publishers:
    /mqtt_txd: std_msgs/msg/String
    /parameter_events: rcl_interfaces/msg/ParameterEvent
    /rosout: rcl_interfaces/msg/Log


#### /mqtt_to_ros_node
  Subscribers:
    /diablo/sensor/Battery: sensor_msgs/msg/BatteryState
    /fix: sensor_msgs/msg/NavSatFix
    /mqtt_txd: std_msgs/msg/String
  Publishers:
    /cmd_vel: geometry_msgs/msg/Twist
    /led: std_msgs/msg/String
    /mqtt_rxd: std_msgs/msg/String
    /parameter_events: rcl_interfaces/msg/ParameterEvent
    /rosout: rcl_interfaces/msg/Log
    /stand: std_msgs/msg/String



### 4) 外设控制：氛围灯
不重要

### 5) 机器人控制：底盘控制 + 站立控制 + 简易 UI
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



### 6) 坐标系：机器人静态/动态 TF
静态TF发布
'base_footprint','base_link'
'base_link', 'diablo_robot'
'base_link', 'livox_frame'
'base_link', 'camera_link'
#### display_no_rviz.launch.py
发布了两个节点
robot_state_publisher
joint_state_publisher/joint_state_publisher_gui

##### robot_state_publisher
读取URDF，运动学计算与坐标变换发布
/robot_state_publisher
  Subscribers:
    /joint_states: sensor_msgs/msg/JointState

  Publishers:
    /robot_description: std_msgs/msg/String     # URDF
    /tf: tf2_msgs/msg/TFMessage                 # 动态TF
    /tf_static: tf2_msgs/msg/TFMessage          # 静态TF


##### joint_state_publisher/joint_state_publisher_gui
解析 URDF 模型，为所有非固定关节生成并发布角度数据
发布关节角到 joint_states

/joint_state_publisher
  Subscribers:
    /robot_description: std_msgs/msg/String
  Publishers:
    /joint_states: sensor_msgs/msg/JointState




--------------------------------------------------------------------------------
### 节点7) 状态估计：融合轮速里程计与 IMU 输出 /odom---第三方库
ekf_filter_node
核心是扩展卡尔曼滤波
把 IMU + 轮式里程计按各自可信度融合
输出更稳定的机器人位姿估计
/ekf_filter_node
  Subscribers:
    /diablo/sensor/Imu: sensor_msgs/msg/Imu
    /diablo_odom: nav_msgs/msg/Odometry                         # 轮式里程计
    /set_pose: geometry_msgs/msg/PoseWithCovarianceStamped      #  RViz 里点“2D Pose Estimate
  Publishers:
    /diagnostics: diagnostic_msgs/msg/DiagnosticArray           # 运行状态和健康信息，用于调试和监控
    /odom: nav_msgs/msg/Odometry
    /tf: tf2_msgs/msg/TFMessage



### 节点8) 感知转换：将 Livox 点云投影为 2D LaserScan 供导航/建图使用---官方节点
pointcloud_to_laserscan_node

### 节点9) 控制消息转换：融合 cmd_vel 与键盘控制消息
msg_convert//ros类当中写的是msg_convert

/msg_convert
  Subscribers:
    /cmd_vel: geometry_msgs/msg/Twist               # 导航来的控制指令
    /key_control: motion_msgs/msg/MotionCtrl        # 

  Publishers:
    /diablo/MotionCmd: motion_msgs/msg/MotionCtrl   # 最终控制消息




### 节点10) 里程计发布：基于电机状态计算轮式里程计
odom_publish_node

/odom_publish_node
  Subscribers:
    /diablo/sensor/Motors: motion_msgs/msg/LegMotors    # 订阅电机状态

  Publishers:
    /diablo_odom: nav_msgs/msg/Odometry                 # 生成里程计消息




## ros2 topic list
/cmd_vel
/diablo/MotionCmd
/diablo/sensor/Battery
/diablo/sensor/Body_state
/diablo/sensor/Imu
/diablo/sensor/ImuEuler
/diablo/sensor/Motors
/diablo_odom
/diagnostics
/fix
/joint_states
/key_control
/led
/mqtt_rxd
/mqtt_txd
/odom
/parameter_events
/robot_description
/rosout
/scan
/set_pose
/stand
/tf
/tf_static


## ros2 node list

/camera/camera                          # 相机
/livox_lidar_publisher                  # 雷达

---------------------------------------------------------


/diablo_ctrl_node                       # 控制
/diablo_stand_node                      # 站立
/UI节点不显示

/odom_publish_node                      # 电机-》轮式里程计
/ekf_filter_node                        # 轮式里程计+IMU-》里程计

/msg_convert                            # 控制指令融合


/mqtt_to_ros_node                       # MQTT
/ros_to_mqtt_publisher                  # MQTT


------------------------------------------------------

/pointcloud_to_laserscan                # 点云转scan

/robot_state_publisher                  # URDF
/joint_state_publisher                  # URDF


/static_transform_publisher
/static_transform_publisher
/static_transform_publisher
/static_transform_publisher
/transform_listener_impl_55a6eec31060
/transform_listener_impl_55e0225a1df0



# 文件结构
src
├── 3rdparty
│   └── small_gicp
├── diablo_perception
│   ├── FASTLIO2_ROS2                  FAST-LIO2 主体，含回环、重定位与地图优化相关组件
│   ├── linefit_ground_segmentation_ros2  地面分割算法（点云地面/非地面分离）
│   ├── loam_interface                 LOAM 系统接口与数据桥接
│   ├── pb_nav2_plugins                Nav2 自定义插件集合
│   ├── pcd2grid                       PCD 点云转栅格地图工具
│   ├── point_lio_ros2                 Point-LIO 激光惯导里程计
│   ├── sensor_scan_generation         传感器坐标系激光扫描生成与转换
│   ├── terrain_analysis               地形分析模块（局部）
│   └── terrain_analysis_ext           扩展地形分析模块（大尺度）
├── diablo_ros2
│   ├── diablo_basic
│   ├── diablo_bringup
│   ├── diablo_convert
│   ├── diablo_description
│   ├── diablo_led
│   ├── diablo_mqtt
│   ├── diablo_navigation2
│   ├── diablo_odom
│   ├── diablo_rviz
│   ├── diablo_slam
│   ├── diablo_visualise
└── utilities
  ├── livox_ros_driver2        Livox 雷达 ROS2 驱动
  ├── nav2_behavior_tree       Nav2 行为树节点与执行框架
  ├── nav2_map_server          地图服务
  ├── nav2_preview_msgs        Nav2 预览/实验用消息定义
  ├── nav2_recoveries          Nav2 恢复行为（后退/旋转/等待等）
  ├── nmea_navsat_driver       GPS/NMEA 数据解析驱动
  ├── pointcloud_to_laserscan  点云转 2D 
  ├── robot_localization       EKF/UKF 多传感器融合定位
  ├── slam_cartographer        Cartographer
  └── slam_gmapping            GMapping


## diablo_ros2

src/diablo_ros2
├── diablo_basic            基础能力层
├── diablo_bringup          启动
├── diablo_convert          控制消息转换层，把 cmd_vel 与键盘控制等输入统一转换为底盘控制消息。
├── diablo_description      机器人坐标系与模型描述，主要提供 TF 关系定义与相关启动文件。
├── diablo_led              氛围灯控制模块
├── diablo_mqttMQTT         通信模块，提供消息接收与发送节点，用于云端/上位机互联。
├── diablo_navigation2      2D 导航模块，包含地图、导航参数与 Nav2 启动文件。
├── diablo_odom             轮式里程计模块，根据电机状态计算并发布机器人里程计信息。
├── diablo_rviz             可视化配置模块，提供常用 RViz 配置文件与启动入口。
├── diablo_slam             建图与定位算法入口，集成 gmapping、slam_toolbox、cartographer 等方案。
├── diablo_visualise        仿真与模型可视化模块，包含 URDF 显示、姿态转换与仿真相关功能。



### diablo_basic

src/diablo_ros2/diablo_basic/
├── diablo_ception      机器人传感器感知模块
│   ├── diablo_body         电量信息+运动状态信息+IMU+电机
├── diablo_common       SDK与通用方法模块
│   ├── diablo_utils        通信协议+crc校验+电机控制协议+串口读写+模拟遥控器发送数据
├── diablo_interaction  控制交互模块
│   ├── diablo_ctrl         获取机器人SDK控制权限
│   ├── diablo_teleop       捕获键盘输入信息
├── diablo_interfaces   自定义消息接口
    ├── ception_msgs        感知
    └── motion_msgs         移动


### diablo_bringup
* [机器人ROS基础驱动模块](./diablo_bringup/)




### diablo_convert
* [机器人运动控制消息转换模块](./diablo_convert/)

### diablo_description
* [机器人TF坐标变换模块](./diablo_description/)

### diablo_led
* [机器人氛围灯控制模块](./diablo_led/)

### diablo_mqtt
* [机器人mqtt平台通信模块](./diablo_mqtt/)

### diablo_navigation2
* [机器人2D导航模块](./diablo_navigation2/)
  > navigation2   (Navfn + DWB) 等

### diablo_odom
* [机器人轮式里程计模块](./diablo_odom/)

### diablo_rviz
* [机器人常用可视化配置模块](./diablo_rviz/)

### diablo_slam
* [机器人环境感知模块](./diablo_slam/)
  > gmapping

  > slam_toolbox

  > cartographer

### diablo_visualise
src/diablo_ros2/diablo_visualise/
├── diablo_simpose_trans
├── diablo_simulation



# 快速启动说明
Ctrl + Alt + t新开一个终端，根据提示依次复制如下命令粘贴进终端，按下Enter键执行

一、启动整机ROS驱动 （使用后续命令，必须先启动本命令）

1. 建议此时机器人为坐下的状态，然后再运行如下命令
ros2 launch diablo_bringup diablo_bringup.launch.py

使用刚建好的地图map_2024-11-14-161721，完整的命令实例如下
ros2 launch diablo_navigation2 nav2.launch.py use_map:=map_2025-11-22-173958  

ctrl+c guanbi


当一直看到终端输出消息为
[mqtt_receive-3] [INFO] [1732670149.210665412] [ros_to_mqtt_publisher]: Received ROS message to publish to MQTT: BATT 12.247
[mqtt_receive-3] [INFO] [1732670150.209887891] [ros_to_mqtt_publisher]: Received ROS message to publish to MQTT: BATT 12.262
........
则表示正常

2. 导航模式站起
ros2 topic pub /stand std_msgs/msg/String "{data: standup}" --once

3. 导航模式蹲下
ros2 topic pub /stand std_msgs/msg/String "{data: sitdown}" --once

4. 开启探照灯
ros2 topic pub /led std_msgs/msg/String "{data: 0 255 0 0}" --once

5. 关闭探照灯
ros2 topic pub /led std_msgs/msg/String "{data: 0 0 0 0}" --once

二、运行2D SLAM算法建立环境地图

首次使用时，请建立一次环境地图，
可以使用的建图算法如下，有gmapping、slam_toolbox、cartographer_2d, 选择其中一个即可

1.Gmapping 建图

ros2 launch diablo_slam gmapping.launch.py 

2.SLAM_TOOLBOX 建图

ros2 launch diablo_slam slam_toolbox.launch.py

3.Cartographer 建图

ros2 launch diablo_slam cartographer_2d.launch.py

三、如何查看当前 2D 栅格地图的建立情况

ros2 launch diablo_rviz view_map.launch.py

四、保存并 2D 栅格地图

ros2 launch diablo_slam map_save.launch.py 

保存地图时，注意在运行该命令的终端中查看保存地图的名称，比如这里地图文件的名称就是`map_2024-11-14-161721`
[map_saver_cli-1] [INFO] [map_io]: Received a 209 X 236 map @ 0.05 m/pix
[map_saver_cli-1] [INFO] [map_io]: Writing map occupancy data to /home/tianbot/diablo_ws/src/diablo_ros2/diablo_navigation2/maps/map_2024-11-14-161721.pgm
[map_saver_cli-1] [INFO] [map_io]: Writing map metadata to /home/tianbot/diablo_ws/src/diablo_ros2/diablo_navigation2/maps/map_2024-11-14-161721.yaml
[map_saver_cli-1] [INFO] [map_io]: Map saved
[map_saver_cli-1] [INFO] [1731572241.580101996] [map_saver_cli]: Map saved successfully
[map_saver_cli-1] [INFO] [1731572241.580286026] [map_saver_cli]: Destroying
[INFO] [map_saver_cli-1]: process has finished cleanly [pid 483871]

五、如何使用刚刚建好的地图进行导航

如果是在云谷二期处导航，可以直接在本机上运行下行命令即可
ros2 launch diablo_navigation2 nav2_xixian.launch.py

ros2 launch diablo_navigation2 nav2.launch.py use_map:=xxxx  #xxx是刚才建立好的地图文件，这里我将xxx替换为map_2024-11-14-161721传入即可

使用刚建好的地图map_2024-11-14-161721，完整的命令实例如下
ros2 launch diablo_navigation2 nav2.launch.py use_map:=map_2025-11-22-173958       /////////sfy05-2

ros2 launch diablo_navigation2 nav2.launch.py use_map:=sfy05

回车运行后，等待5s，导航组件加载完成

六、当导航节点正确运行之后，可以在rviz界面中使用2D Pose Estimate工具，鼠标点击后，保持鼠标左键按下选定好箭头方向后再松开，以此给定机器人当前的初始位置和姿态朝向，正确给定后，即可看到地图膨胀层出现

七、此时可以开始 2D 导航，使用2D Nav Goal工具，鼠标点击后，保持鼠标左键按下选定好箭头方向后再松开，以给定目标点，此时rviz中会出现一条规划好的全局路径，（如果没有出现，请重新给点后再尝试）

！！！！！！注意使用2D Pose Estimate和2D Nav Goal工具时，不要点击到rviz中的膨胀区域上，可能导致机器人无法正确完成导航任务。
！！！！！！如该机器人在给定目标点后，出现全局路径，但是机器人没有移动，需要检查你的遥控器此时是否处于禁用模式下



# 建图---cartographer_2d

## ros2 launch diablo_slam cartographer_2d.launch.py
启动了三个节点
cartographer_node---官方
cartographer_occupancy_grid_node---官方
rviz2




## ros2 launch diablo_rviz view_map.launch.py



## ros2 launch diablo_slam map_save.launch.py 



# 导航---官方导航
存在bug：map->odom没有找到-----解决：在rviz当中给出初始位置姿态
## ros2 launch diablo_navigation2 nav2.launch.py use_map:=map_2025-11-22-173958 

bringup_launch.py---官方
rviz2

### bringup_launch.py（humble/nav2_bringup/launch/bringup_launch.py）

节点
nav2_container

launch文件
slam_launch.py
localization_launch.py
navigation_launch.py



# odin基础移植


