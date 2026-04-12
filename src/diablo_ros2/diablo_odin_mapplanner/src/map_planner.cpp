#include "diablo_odin_mapplanner/map_planner.hpp"

#include <geometry_msgs/msg/transform_stamped.hpp>
#include <tf2_geometry_msgs/tf2_geometry_msgs.h>

#include <algorithm>
#include <cmath>
#include <limits>
#include <queue>
#include <vector>

namespace
{
struct GridNode
{
  int index;
  double g;
  double f;

  bool operator>(const GridNode & other) const
  {
    return f > other.f;
  }
};

constexpr double kSqrt2 = 1.41421356237;
}  // namespace

namespace diablo_odin_mapplanner
{

MapPlanner::MapPlanner(const rclcpp::NodeOptions & options)
: Node("map_planner", options)
{
  this->declare_parameter("inflation_radius", inflation_radius_);
  this->declare_parameter("obstacle_threshold", obstacle_threshold_);
  this->declare_parameter("publish_path", publish_path_);
  this->declare_parameter("service_name", plan_service_name_);
  this->declare_parameter("map_frame", map_frame_);
  this->declare_parameter("base_frame", base_frame_);

  this->get_parameter("inflation_radius", inflation_radius_);
  this->get_parameter("obstacle_threshold", obstacle_threshold_);
  this->get_parameter("publish_path", publish_path_);
  this->get_parameter("service_name", plan_service_name_);
  this->get_parameter("map_frame", map_frame_);
  this->get_parameter("base_frame", base_frame_);

  tf_buffer_ = std::make_unique<tf2_ros::Buffer>(this->get_clock());
  tf_listener_ = std::make_shared<tf2_ros::TransformListener>(*tf_buffer_);

  path_pub_ = this->create_publisher<nav_msgs::msg::Path>("initial_path", rclcpp::QoS(1).transient_local());
  inflated_map_pub_ =
    this->create_publisher<nav_msgs::msg::OccupancyGrid>("inflated_map", rclcpp::QoS(1).transient_local());
  plan_result_pub_ = this->create_publisher<std_msgs::msg::Bool>("/map_planner/result", rclcpp::QoS(1));

  map_sub_ = this->create_subscription<nav_msgs::msg::OccupancyGrid>(
    "map", rclcpp::QoS(1).transient_local(),
    std::bind(&MapPlanner::mapCallback, this, std::placeholders::_1));
  goal_sub_ = this->create_subscription<geometry_msgs::msg::PoseStamped>(
    "/move_base_simple/goal", rclcpp::QoS(1),
    std::bind(&MapPlanner::goalCallback, this, std::placeholders::_1));

  plan_service_ = this->create_service<srv::PlanPath>(
    plan_service_name_, std::bind(
      &MapPlanner::planService, this, std::placeholders::_1, std::placeholders::_2,
      std::placeholders::_3));

  RCLCPP_INFO(this->get_logger(), "Map planner started with service: %s", plan_service_name_.c_str());
}

void MapPlanner::mapCallback(const nav_msgs::msg::OccupancyGrid::SharedPtr msg)
{
  map_ = *msg;
  if (map_.info.resolution <= 0.0) {
    RCLCPP_WARN_THROTTLE(this->get_logger(), *this->get_clock(), 5000, "Map resolution invalid.");
    map_ready_ = false;
    return;
  }

  inflation_cells_ = std::max(1, static_cast<int>(std::ceil(inflation_radius_ / map_.info.resolution)));
  inflateMap();
  map_ready_ = true;
  map_frame_ = map_.header.frame_id.empty() ? map_frame_ : map_.header.frame_id;
  publishInflatedMap();
  RCLCPP_INFO_ONCE(this->get_logger(), "Inflated map ready for planning.");
}

void MapPlanner::goalCallback(const geometry_msgs::msg::PoseStamped::SharedPtr goal)
{
  if (!map_ready_) {
    RCLCPP_WARN_THROTTLE(this->get_logger(), *this->get_clock(), 2000, "Map not ready for planning.");
    publishPlanResult(false);
    return;
  }

  geometry_msgs::msg::PoseStamped start_pose;
  if (!getRobotPose(start_pose)) {
    RCLCPP_WARN_THROTTLE(this->get_logger(), *this->get_clock(), 2000, "Unable to get robot pose.");
    publishPlanResult(false);
    return;
  }

  geometry_msgs::msg::PoseStamped goal_in_map = *goal;
  if (goal->header.frame_id.empty()) {
    goal_in_map.header.frame_id = map_frame_;
  }

  if (goal_in_map.header.frame_id != map_frame_) {
    try {
      const geometry_msgs::msg::TransformStamped tf_stamped = tf_buffer_->lookupTransform(
        map_frame_, goal_in_map.header.frame_id, tf2::TimePointZero, tf2::durationFromSec(0.1));
      tf2::doTransform(*goal, goal_in_map, tf_stamped);
    } catch (const tf2::TransformException & ex) {
      RCLCPP_WARN_THROTTLE(
        this->get_logger(), *this->get_clock(), 2000, "Goal transform failed: %s", ex.what());
      publishPlanResult(false);
      return;
    }
  }

  nav_msgs::msg::Path path;
  const bool success = plan(start_pose, goal_in_map, path);
  publishPlanResult(success);

  if (!success) {
    RCLCPP_WARN(this->get_logger(), "Failed to plan a path.");
    return;
  }

  path_pub_->publish(path);
}

void MapPlanner::planService(
  const std::shared_ptr<rmw_request_id_t> request_header,
  const std::shared_ptr<srv::PlanPath::Request> req,
  std::shared_ptr<srv::PlanPath::Response> res)
{
  (void)request_header;

  if (!map_ready_) {
    RCLCPP_WARN_THROTTLE(this->get_logger(), *this->get_clock(), 2000, "Map not ready for planning.");
    publishPlanResult(false);
    return;
  }

  geometry_msgs::msg::PoseStamped start_pose;
  if (!getRobotPose(start_pose)) {
    RCLCPP_WARN_THROTTLE(this->get_logger(), *this->get_clock(), 2000, "Unable to get robot pose.");
    publishPlanResult(false);
    return;
  }

  geometry_msgs::msg::PoseStamped goal = req->goal;
  if (goal.header.frame_id.empty()) {
    goal.header.frame_id = map_frame_;
  }

  if (goal.header.frame_id != map_frame_) {
    try {
      const geometry_msgs::msg::TransformStamped tf_stamped = tf_buffer_->lookupTransform(
        map_frame_, goal.header.frame_id, tf2::TimePointZero, tf2::durationFromSec(0.1));
      geometry_msgs::msg::PoseStamped transformed;
      tf2::doTransform(goal, transformed, tf_stamped);
      goal = transformed;
    } catch (const tf2::TransformException & ex) {
      RCLCPP_WARN(this->get_logger(), "Goal transform failed: %s", ex.what());
      publishPlanResult(false);
      return;
    }
  }

  nav_msgs::msg::Path path;
  const bool success = plan(start_pose, goal, path);
  publishPlanResult(success);
  if (!success) {
    RCLCPP_WARN(this->get_logger(), "Failed to plan a path.");
    return;
  }

  res->path = path;
  if (publish_path_) {
    path_pub_->publish(path);
  }
}

bool MapPlanner::getRobotPose(geometry_msgs::msg::PoseStamped & pose) const
{
  try {
    const geometry_msgs::msg::TransformStamped tf = tf_buffer_->lookupTransform(
      map_frame_, base_frame_, tf2::TimePointZero, tf2::durationFromSec(0.2));
    pose.header = tf.header;
    pose.pose.position.x = tf.transform.translation.x;
    pose.pose.position.y = tf.transform.translation.y;
    pose.pose.position.z = tf.transform.translation.z;
    pose.pose.orientation = tf.transform.rotation;
    return true;
  } catch (const tf2::TransformException & ex) {
    RCLCPP_WARN(this->get_logger(), "TF lookup failed: %s", ex.what());
    return false;
  }
}

bool MapPlanner::plan(
  const geometry_msgs::msg::PoseStamped & start,
  const geometry_msgs::msg::PoseStamped & goal,
  nav_msgs::msg::Path & path) const
{
  int start_x = 0;
  int start_y = 0;
  int goal_x = 0;
  int goal_y = 0;

  if (!worldToMap(start.pose.position, start_x, start_y) || !worldToMap(goal.pose.position, goal_x, goal_y)) {
    RCLCPP_WARN(this->get_logger(), "Start or goal outside the map.");
    return false;
  }

  const int width = static_cast<int>(map_.info.width);
  const int height = static_cast<int>(map_.info.height);
  const int start_index = toIndex(start_x, start_y);
  const int goal_index = toIndex(goal_x, goal_y);

  if (!isFree(start_index) || !isFree(goal_index)) {
    RCLCPP_WARN(this->get_logger(), "Start or goal is occupied.");
    return false;
  }

  std::vector<double> g_score(static_cast<size_t>(width * height), std::numeric_limits<double>::infinity());
  std::vector<int> came_from(static_cast<size_t>(width * height), -1);
  std::priority_queue<GridNode, std::vector<GridNode>, std::greater<GridNode>> open_set;

  const auto heuristic = [&](int mx, int my) {
    const double dx = static_cast<double>(mx - goal_x);
    const double dy = static_cast<double>(my - goal_y);
    return std::hypot(dx, dy);
  };

  g_score[start_index] = 0.0;
  open_set.push({start_index, 0.0, heuristic(start_x, start_y)});

  constexpr int dx[8] = {1, -1, 0, 0, 1, 1, -1, -1};
  constexpr int dy[8] = {0, 0, 1, -1, 1, -1, 1, -1};
  constexpr double costs[8] = {1.0, 1.0, 1.0, 1.0, kSqrt2, kSqrt2, kSqrt2, kSqrt2};

  while (!open_set.empty()) {
    const GridNode current = open_set.top();
    open_set.pop();

    if (current.index == goal_index) {
      break;
    }

    const int cx = current.index % width;
    const int cy = current.index / width;

    for (int i = 0; i < 8; ++i) {
      const int nx = cx + dx[i];
      const int ny = cy + dy[i];
      if (nx < 0 || ny < 0 || nx >= width || ny >= height) {
        continue;
      }

      const int n_index = toIndex(nx, ny);
      if (!isFree(n_index)) {
        continue;
      }

      const double tentative_g = g_score[current.index] + costs[i];
      if (tentative_g < g_score[n_index]) {
        came_from[n_index] = current.index;
        g_score[n_index] = tentative_g;
        const double f_score = tentative_g + heuristic(nx, ny);
        open_set.push({n_index, tentative_g, f_score});
      }
    }
  }

  if (came_from[goal_index] == -1 && goal_index != start_index) {
    return false;
  }

  std::vector<int> index_path;
  for (int current = goal_index; current != -1; current = came_from[current]) {
    index_path.push_back(current);
    if (current == start_index) {
      break;
    }
  }

  if (index_path.empty() || index_path.back() != start_index) {
    return false;
  }

  std::reverse(index_path.begin(), index_path.end());

  path.header.stamp = this->now();
  path.header.frame_id = map_frame_;
  path.poses.reserve(index_path.size());

  for (const int idx : index_path) {
    const int mx = idx % width;
    const int my = idx / width;
    geometry_msgs::msg::PoseStamped pose;
    pose.header = path.header;
    pose.pose.position = mapToWorld(mx, my);
    pose.pose.orientation.w = 1.0;
    path.poses.push_back(pose);
  }

  return true;
}

void MapPlanner::inflateMap()
{
  inflated_data_ = map_.data;
  if (inflation_cells_ <= 0) {
    return;
  }

  const int width = static_cast<int>(map_.info.width);
  const int height = static_cast<int>(map_.info.height);
  std::vector<int8_t> result = inflated_data_;

  for (int y = 0; y < height; ++y) {
    for (int x = 0; x < width; ++x) {
      const int index = toIndex(x, y);
      if (map_.data[static_cast<size_t>(index)] < obstacle_threshold_ ||
        map_.data[static_cast<size_t>(index)] < 0)
      {
        continue;
      }

      for (int dy = -inflation_cells_; dy <= inflation_cells_; ++dy) {
        for (int dx = -inflation_cells_; dx <= inflation_cells_; ++dx) {
          const int nx = x + dx;
          const int ny = y + dy;
          if (nx < 0 || ny < 0 || nx >= width || ny >= height) {
            continue;
          }
          if (std::hypot(dx, dy) * map_.info.resolution > inflation_radius_) {
            continue;
          }
          result[static_cast<size_t>(toIndex(nx, ny))] = 100;
        }
      }
    }
  }

  inflated_data_.swap(result);
}

void MapPlanner::publishInflatedMap()
{
  nav_msgs::msg::OccupancyGrid inflated = map_;
  inflated.header.stamp = this->now();
  inflated.data = inflated_data_;
  inflated_map_pub_->publish(inflated);
}

void MapPlanner::publishPlanResult(bool success)
{
  std_msgs::msg::Bool msg;
  msg.data = success;
  plan_result_pub_->publish(msg);
}

bool MapPlanner::worldToMap(const geometry_msgs::msg::Point & point, int & mx, int & my) const
{
  if (!map_ready_) {
    return false;
  }

  const double origin_x = map_.info.origin.position.x;
  const double origin_y = map_.info.origin.position.y;
  const double resolution = map_.info.resolution;

  mx = static_cast<int>(std::floor((point.x - origin_x) / resolution));
  my = static_cast<int>(std::floor((point.y - origin_y) / resolution));

  return mx >= 0 && my >= 0 &&
         mx < static_cast<int>(map_.info.width) && my < static_cast<int>(map_.info.height);
}

geometry_msgs::msg::Point MapPlanner::mapToWorld(int mx, int my) const
{
  geometry_msgs::msg::Point point;
  point.x = map_.info.origin.position.x + (static_cast<double>(mx) + 0.5) * map_.info.resolution;
  point.y = map_.info.origin.position.y + (static_cast<double>(my) + 0.5) * map_.info.resolution;
  point.z = 0.0;
  return point;
}

int MapPlanner::toIndex(int mx, int my) const
{
  return my * static_cast<int>(map_.info.width) + mx;
}

bool MapPlanner::isFree(int index) const
{
  if (index < 0 || static_cast<size_t>(index) >= inflated_data_.size()) {
    return false;
  }
  const int8_t value = inflated_data_[static_cast<size_t>(index)];
  if (value < 0) {
    return false;
  }
  return value < obstacle_threshold_;
}

}  // namespace diablo_odin_mapplanner

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<diablo_odin_mapplanner::MapPlanner>());
  rclcpp::shutdown();
  return 0;
}
