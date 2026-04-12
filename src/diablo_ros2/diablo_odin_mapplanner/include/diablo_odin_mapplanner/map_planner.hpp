#pragma once

#include <geometry_msgs/msg/point.hpp>
#include <geometry_msgs/msg/pose_stamped.hpp>
#include <nav_msgs/msg/occupancy_grid.hpp>
#include <nav_msgs/msg/path.hpp>
#include <rclcpp/rclcpp.hpp>
#include <std_msgs/msg/bool.hpp>
#include <tf2_ros/buffer.h>
#include <tf2_ros/transform_listener.h>

#include <string>
#include <vector>

#include "diablo_odin_mapplanner/srv/plan_path.hpp"

namespace diablo_odin_mapplanner
{

class MapPlanner : public rclcpp::Node
{
public:
  explicit MapPlanner(const rclcpp::NodeOptions & options = rclcpp::NodeOptions());

private:
  void mapCallback(const nav_msgs::msg::OccupancyGrid::SharedPtr msg);
  void goalCallback(const geometry_msgs::msg::PoseStamped::SharedPtr goal);
  void planService(
    const std::shared_ptr<rmw_request_id_t> request_header,
    const std::shared_ptr<srv::PlanPath::Request> req,
    std::shared_ptr<srv::PlanPath::Response> res);

  bool getRobotPose(geometry_msgs::msg::PoseStamped & pose) const;
  bool plan(
    const geometry_msgs::msg::PoseStamped & start,
    const geometry_msgs::msg::PoseStamped & goal,
    nav_msgs::msg::Path & path) const;
  void inflateMap();
  void publishInflatedMap();
  void publishPlanResult(bool success);

  bool worldToMap(const geometry_msgs::msg::Point & point, int & mx, int & my) const;
  geometry_msgs::msg::Point mapToWorld(int mx, int my) const;
  int toIndex(int mx, int my) const;
  bool isFree(int index) const;

  rclcpp::Subscription<nav_msgs::msg::OccupancyGrid>::SharedPtr map_sub_;
  rclcpp::Subscription<geometry_msgs::msg::PoseStamped>::SharedPtr goal_sub_;
  rclcpp::Publisher<nav_msgs::msg::Path>::SharedPtr path_pub_;
  rclcpp::Publisher<nav_msgs::msg::OccupancyGrid>::SharedPtr inflated_map_pub_;
  rclcpp::Publisher<std_msgs::msg::Bool>::SharedPtr plan_result_pub_;
  rclcpp::Service<srv::PlanPath>::SharedPtr plan_service_;

  nav_msgs::msg::OccupancyGrid map_;
  std::vector<int8_t> inflated_data_;

  bool map_ready_{false};
  bool publish_path_{true};
  double inflation_radius_{0.25};
  int obstacle_threshold_{50};
  int inflation_cells_{1};

  std::string plan_service_name_{"/map_planner/plan"};
  std::string map_frame_{"map"};
  std::string base_frame_{"odin1_base_link"};

  std::unique_ptr<tf2_ros::Buffer> tf_buffer_;
  std::shared_ptr<tf2_ros::TransformListener> tf_listener_;
};

}  // namespace diablo_odin_mapplanner
