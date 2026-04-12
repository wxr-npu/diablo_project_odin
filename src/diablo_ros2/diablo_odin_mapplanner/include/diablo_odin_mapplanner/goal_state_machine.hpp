#pragma once

#include <geometry_msgs/msg/pose_stamped.hpp>
#include <rclcpp/rclcpp.hpp>
#include <std_msgs/msg/empty.hpp>
#include <tf2_ros/buffer.h>
#include <tf2_ros/transform_listener.h>

#include <string>

#include "diablo_odin_mapplanner/srv/plan_path.hpp"

namespace diablo_odin_mapplanner
{

class GoalStateMachine : public rclcpp::Node
{
public:
  explicit GoalStateMachine(const rclcpp::NodeOptions & options = rclcpp::NodeOptions());

private:
  void arriveCallback(const std_msgs::msg::Empty::SharedPtr msg);
  void goalCallback(const geometry_msgs::msg::PoseStamped::SharedPtr goal);
  bool getRobotPose(geometry_msgs::msg::PoseStamped & pose) const;

  rclcpp::Subscription<std_msgs::msg::Empty>::SharedPtr arrive_sub_;
  rclcpp::Subscription<geometry_msgs::msg::PoseStamped>::SharedPtr goal_sub_;
  rclcpp::Client<srv::PlanPath>::SharedPtr plan_client_;

  geometry_msgs::msg::PoseStamped last_goal_;
  bool have_goal_{false};

  double goal_tolerance_{0.3};
  std::string plan_service_name_{"/map_planner/plan"};
  std::string map_frame_{"map"};
  std::string base_frame_{"odin1_base_link"};

  std::unique_ptr<tf2_ros::Buffer> tf_buffer_;
  std::shared_ptr<tf2_ros::TransformListener> tf_listener_;
};

}  // namespace diablo_odin_mapplanner
