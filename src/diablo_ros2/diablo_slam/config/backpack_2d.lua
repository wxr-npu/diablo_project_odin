-- Copyright 2016 The Cartographer Authors
--
-- Licensed under the Apache License, Version 2.0 (the "License");
-- you may not use this file except in compliance with the License.
-- You may obtain a copy of the License at
--
--      http://www.apache.org/licenses/LICENSE-2.0
--
-- Unless required by applicable law or agreed to in writing, software
-- distributed under the License is distributed on an "AS IS" BASIS,
-- WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
-- See the License for the specific language governing permissions and
-- limitations under the License.

include "map_builder.lua"
include "trajectory_builder.lua"

options = {
  map_builder = MAP_BUILDER,
  trajectory_builder = TRAJECTORY_BUILDER,
  map_frame = "map",
  tracking_frame = "livox_frame",
  -- tracking_frame = "base_footprint",
  published_frame = "odom",
  odom_frame = "odom",
  --设置为true，cartographer会发布一个 odom 坐标系；--程序正常运行，使用ros2 run tf2_tools view_frames可以看到map->odom->lidar_link;
  provide_odom_frame = false,
  publish_frame_projected_to_2d = false,
  use_pose_extrapolator = true,
  use_odometry = true,
  use_nav_sat = false,
  use_landmarks = false,
  --订阅的lidar scan数量
  num_laser_scans = 1,
  num_multi_echo_laser_scans = 0,
  --扫描分割数量，为1不分割
  num_subdivisions_per_laser_scan = 1,
  num_point_clouds = 0,
  lookup_transform_timeout_sec = 0.2,
  submap_publish_period_sec = 0.3,
  pose_publish_period_sec = 5e-3,    --1/5e-3 = 200hz
  trajectory_publish_period_sec = 30e-3,
  rangefinder_sampling_ratio = 1.,
  odometry_sampling_ratio = 1.,
  fixed_frame_pose_sampling_ratio = 1.,
  imu_sampling_ratio = 1.,
  landmarks_sampling_ratio = 1.,
}

-- map_builder
-- 是否使用2d建图
MAP_BUILDER.use_trajectory_builder_2d = true

-- trajectory_builder_2d
TRAJECTORY_BUILDER_2D.submaps.num_range_data = 35
-- 根据激光雷达的性能，最小范围
TRAJECTORY_BUILDER_2D.min_range = 0.10
-- 根据激光雷达的性能，最大范围
TRAJECTORY_BUILDER_2D.max_range = 30
-- 无效激光数据设置距离为该值
TRAJECTORY_BUILDER_2D.missing_data_ray_length = 3.
-- false,不使用IMU数据
TRAJECTORY_BUILDER_2D.use_imu_data = true
-- true,使用实时回环检测来进行前端的扫描匹配
TRAJECTORY_BUILDER_2D.use_online_correlative_scan_matching = true
--尽量小点；如果移动距离或旋转过小, 或者时间过短, 不进行地图的更新
TRAJECTORY_BUILDER_2D.motion_filter.max_angle_radians = math.rad(0.1)
--FastCorrelativeScanMatcher初步匹配的结果分数，高于此分数才进入下一步的Ceres Scan Matcher处理。

-- pose graph
POSE_GRAPH.constraint_builder.min_score = 0.65
--全局定位最小分数，低于此分数则认为目前全局定位不准确
POSE_GRAPH.constraint_builder.global_localization_min_score = 0.7

return options
