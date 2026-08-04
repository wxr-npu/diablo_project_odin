# Diablo ROS2 导航交接说明

本文档用于交接当前 ROS2 导航移植与测试进度，重点回答三件事：
1. 我已经做了什么
2. 我现在卡在哪里
3. 交接后希望你给我什么支持

## 1. 我做了什么（已完成）

### 1.1 导航链路已跑通（Odin + 全局规划 + NeuPAN）
- 终端1：启动底层驱动与控制链路
  - `ros2 launch diablo_bringup diablo_bringup_odin.launch.py`
  - 包含 Odin 驱动、底盘控制、`msg_convert`（`/cmd_vel -> /diablo/MotionCmd`）
- 终端2：启动地图服务与全局规划
  - `ros2 launch diablo_odin_mapplanner whole.launch.py`
  - 包含 `map_server`、`map_planner`、`goal_state_machine`
- 终端3：启动 NeuPAN 局部规划
  - `python src/diablo_ros2/diablo_neupan/diablo_neupan/neupan_ros2.py`

### 1.2 建图与重定位流程已打通
- 建图脚本：
  - `bash src/diablo_perception/odin_ros_driver/script/map_recording_ros2.sh mapname`
- 已完成从 Odin 点云到地图文件的完整产物链：
  - 点云录制：`/odin1/cloud_slam -> *.pcd`
  - 栅格地图：`*.yaml/*.pgm`
  - 重定位地图：`*.bin`
- 已验证通过修改 `control_command.yaml` 的 `custom_map_mode` 与 `relocalization_map_abs_path` 进行重定位切换。

### 1.3 关键历史问题已修复并验证
- “到点后原地转圈”问题已修复：
  - 在 `diablo_convert/msg_convert.cpp` 增加 `cmd_vel` 超时失效逻辑（避免旧速度残留）
  - NeuPAN 在到点/停止时主动持续发零速

## 2. 现在遇到的问题（待解决）

### 2.1 当前测试现状
1. 宿舍走廊场景：建图与重定位效果较好。
2. 户外中小场景：建图与重定位基本可用，但转 2D 栅格图后，轨迹附近会出现黑色障碍区域（疑似地面/低矮结构被误判为障碍）。
3. 大型户外场景：`map_20260414_152654.bin` 重定位失败。
4. 花园场景：重定位失败。

### 2.2 问题影响
- 目前系统在室内和中小场景可用，但在大型户外场景稳定性不足。
- 主要瓶颈是重定位鲁棒性与点云到 2D 栅格映射质量。

### 2.3 初步判断
- 仅依赖 Odin 做大场景重定位能力不足。
- 户外复杂地形下，点云转 LaserScan / 2D 栅格时参数需要进一步针对地面与低矮障碍物做过滤。
- 后续大场景需要考虑 GPS 融合，而不是只靠纯激光重定位。

## 3. 诉求

### 3.1 请优先支持的技术方向
1. 大场景重定位方案
	- 帮忙评估并落地 GPS 融合方案，用于户外长距离与重复纹理弱场景。
2. 地图质量优化
	- 协助调整点云到 2D 栅格的过滤与高度阈值，减少“轨迹黑边/黑块误障碍”。
3. 稳定性回归验证
	- 给出一套固定测试路线与验收标准（成功率、重定位时延、到点误差）。

### 3.2 继续推进
1. 一份可执行的户外大场景定位融合方案（参数建议 + 启动方式）。



## 4. 当前导航逻辑

注：局部规划器仍使用 NeuPAN。

1. `nav2_map_server/map_server`
	- 加载静态地图。
2. `nav2_lifecycle_manager/lifecycle_manager`
	- 管理 map_server 生命周期。
3. `pointcloud_to_laserscan/pointcloud_to_laserscan_node`
	- 点云转 2D LaserScan。
4. `/map_planner_node`
	- 全局规划。
	- 订阅：`/map`、`/move_base_simple/goal`
	- 发布：`/initial_path`、`/inflated_map`、`/map_planner/result`
5. `/goal_state_machine_node`
	- 处理到达事件和重规划。
	- 订阅：`/neupan/arrive`、`/move_base_simple/goal`


## 5. 工程链接

https://github.com/wxr-npu/007_diablo_test/tree/delete_modules

---

# Diablo ROS2 导航系统说明

本文档用于当前工程的日常使用与排障，覆盖以下目标：
- Odin 驱动 + 地图服务 + 全局规划 + 局部规划（NeuPAN）完整链路
- 建图、重定位、导航三类场景
- 常见故障快速定位（重点：到点后转圈、给点不走）


后续规划：
在大型室外场景当中，需要融合GPS信息，单靠odin无法完成重定位

## 1. 工程结构（核心模块）

```text
src/
├── diablo_ros2/
│   ├── diablo_bringup         机器人基础驱动启动
│   ├── diablo_convert         cmd_vel -> MotionCtrl 转换层
│   ├── diablo_odom            电机状态 -> 轮式里程计
│   ├── diablo_navigation2     Nav2 地图与导航配置
│   ├── diablo_slam            建图入口（gmapping/slam_toolbox/cartographer）
│   ├── diablo_rviz            可视化配置
│   └── diablo_neupan          NeuPAN 局部规划（Python）
├── diablo_perception/
│   └── odin_ros_driver        Odin 传感器驱动与建图脚本
└── utilities/
    ├── nav2_map_server
    └── pointcloud_to_laserscan
```

## 2. 当前导航链路（Odin + NeuPAN）

运行时通常分 3 个终端：

1. 终端1：底层驱动与控制链路

```bash
source /opt/ros/galactic/setup.bash
source /home/tianbot/diablo_ws/install/setup.bash
ros2 launch diablo_bringup diablo_bringup_odin.launch.py
```

2. 终端2：地图与全局规划

```bash
source /opt/ros/galactic/setup.bash
source /home/tianbot/diablo_ws/install/setup.bash
ros2 launch diablo_odin_mapplanner whole.launch.py
```

3. 终端3：NeuPAN 局部规划

```bash
source /opt/ros/galactic/setup.bash
source /home/tianbot/diablo_ws/install/setup.bash
source ~/miniconda3_new/etc/profile.d/conda.sh
conda activate neupan38
python /home/tianbot/diablo_ws/src/diablo_ros2/diablo_neupan/diablo_neupan/neupan_ros2.py
```

## 3. 核心节点职责

### 3.1 终端1（底层）
- /diablo_ctrl_node
  - 订阅 /diablo/MotionCmd
  - 与底盘 SDK 通信，真实执行运动
- /msg_convert
  - 订阅 /cmd_vel、/key_control
  - 发布 /diablo/MotionCmd
- /odom_publish_node
  - 电机状态 -> /diablo_odom
- /ekf_filter_node
  - 融合 IMU + /diablo_odom -> /odom 与 TF

### 3.2 终端2（全局）
- /map_server + lifecycle_manager
  - 静态地图服务
- /map_planner
  - 全局路径规划（A*）
- /goal_state_machine
  - 到达事件与重规划状态管理
- /pc_to_scan
  - /odin1/cloud_slam -> /scan

### 3.3 终端3（局部）
- /neupan_node
  - 订阅 path/scan/goal
  - 发布 /cmd_vel
  - 到点发布 /neupan/arrive

## 4. 关键话题检查

```bash
ros2 topic list
```

最低要求：
- 控制链路：/cmd_vel、/diablo/MotionCmd
- 定位链路：/odom、/tf、/tf_static
- 感知链路：/scan
- 规划链路：/initial_path、/move_base_simple/goal、/neupan/arrive

## 5. 快速操作

### 5.1 站起/蹲下

```bash
ros2 topic pub /stand std_msgs/msg/String "{data: standup}" --once
ros2 topic pub /stand std_msgs/msg/String "{data: sitdown}" --once
```

### 5.2 灯控

```bash
ros2 topic pub /led std_msgs/msg/String "{data: 0 255 0 0}" --once
ros2 topic pub /led std_msgs/msg/String "{data: 0 0 0 0}" --once
```

## 6. ROS2 建图与重定位（Odin）

### 6.1 建图
1. 编辑 odin_ros_driver/config/control_command.yaml
   - custom_map_mode: 1
2. 启动终端1（diablo_bringup_odin）
3. 执行建图脚本

```bash
bash src/diablo_perception/odin_ros_driver/script/map_recording_ros2.sh mapname
```

若脚本阻塞：

```bash
pkill -f pcd2pgm_ros2_node || true
```

产物：
- PCD：src/diablo_perception/odin_ros_driver/odin_map/pcd/
- BIN：src/diablo_perception/odin_ros_driver/odin_map/
- PGM/YAML：src/diablo_ros2/diablo_navigation2/maps/odin_maps/

### 6.2 重定位
1. 编辑 control_command.yaml
   - custom_map_mode: 2
   - relocalization_map_abs_path: BIN 文件绝对路径
2. 启动终端1
3. 检查 TF 链路 map -> odom -> odin1_base_link

## 7. 导航前检查清单（强烈建议）

1. 已站起，且遥控器不在禁用模式
2. RViz 已正确给 initial pose
3. /scan 有数据
4. /initial_path 非空
5. /cmd_vel 与 /diablo/MotionCmd 连续更新
6. TF 连通：map -> odom -> odin1_base_link

## 8. 常见问题与排查

### 8.1 现象：给了目标点，机器人不前进
按顺序执行：

```bash
ros2 topic echo /move_base_simple/goal --once
ros2 topic echo /initial_path --once
ros2 topic hz /cmd_vel
ros2 topic echo /diablo/MotionCmd
ros2 run tf2_ros tf2_echo map odin1_base_link
ros2 topic hz /scan
```

判定逻辑：
- 无 goal：RViz 或 remap 问题
- goal 有但无 path：全局规划或地图问题
- path 有但无 cmd_vel：局部规划输入异常（scan/tf/path）
- cmd_vel 有但 MotionCmd 不对：转换层问题
- MotionCmd 正常但底盘不动：底层执行权限或模式问题

### 8.2 现象：到点后仍原地转圈（已修复）

根因（历史问题）：
- msg_convert 曾缓存上一帧 cmd_vel 并定时重复发布
- 上游停发后旧角速度未失效，导致底盘持续自转

修复内容：
1. 在 diablo_convert/msg_convert.cpp 增加 cmd_vel 超时失效机制
   - 参数：cmd_vel_timeout_sec（默认 0.25s）
   - 参数：cmd_vel_deadband（默认 1e-3）
2. 在超时后强制清零 forward/left，避免旧速度残留
3. 在 neupan_ros2.py 中，stop/arrive 时主动持续发布零速

建议验证：

```bash
ros2 topic hz /cmd_vel
ros2 topic echo /cmd_vel
ros2 topic echo /diablo/MotionCmd
```

期望：到点后两者都快速收敛到 0。

### 8.3 现象：rqt_tf_tree 启动失败（participant index）

建议统一设置：

```bash
source /opt/ros/galactic/setup.bash
source /home/tianbot/diablo_ws/install/setup.bash
export ROS_DOMAIN_ID=5
export ROS_LOCALHOST_ONLY=1
export CYCLONEDDS_URI='<CycloneDDS><Domain id="any"><Discovery><ParticipantIndex>auto</ParticipantIndex><MaxAutoParticipantIndex>300</MaxAutoParticipantIndex></Discovery></Domain></CycloneDDS>'
ros2 daemon stop
ros2 run rqt_tf_tree rqt_tf_tree
```

## 9. 关键启动命令汇总

```bash
# 终端1
ros2 launch diablo_bringup diablo_bringup_odin.launch.py

# 终端2
ros2 launch diablo_odin_mapplanner whole.launch.py

# 终端3
python /home/tianbot/diablo_ws/src/diablo_ros2/diablo_neupan/diablo_neupan/neupan_ros2.py
```

