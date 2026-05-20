#include "diablo_odin_mapplanner/goal_state_machine.hpp"

#include <tf2_geometry_msgs/tf2_geometry_msgs.h>

#include <cmath>
#include <memory>

// 该文件实现了一个简单的目标状态机节点：
// - 监听 `/move_base_simple/goal` 存储最新目标（转换为地图坐标系）
// - 监听 `/neupan/arrive` 到达通知，当收到到达但与目标超出容忍距离时，向地图规划器请求重新规划
// - 通过 TF 获取机器人在地图坐标系下的实时位姿

namespace diablo_odin_mapplanner
{

// GoalStateMachine 构造函数：初始化参数、TF、订阅器和规划服务客户端
GoalStateMachine::GoalStateMachine(const rclcpp::NodeOptions & options)
: Node("goal_state_machine", options)
{
  this->declare_parameter("goal_tolerance", goal_tolerance_);
  this->declare_parameter("plan_service", plan_service_name_);
  this->declare_parameter("map_frame", map_frame_);
  this->declare_parameter("base_frame", base_frame_);

  this->get_parameter("goal_tolerance", goal_tolerance_);
  this->get_parameter("plan_service", plan_service_name_);
  this->get_parameter("map_frame", map_frame_);
  this->get_parameter("base_frame", base_frame_);

  tf_buffer_ = std::make_unique<tf2_ros::Buffer>(this->get_clock());
  tf_listener_ = std::make_shared<tf2_ros::TransformListener>(*tf_buffer_);

  // 到达事件：上层模块发布到 /neupan/arrive，表示机器人声称已到达某处
  arrive_sub_ = this->create_subscription<std_msgs::msg::Empty>(
    "/neupan/arrive", rclcpp::QoS(1),
    std::bind(&GoalStateMachine::arriveCallback, this, std::placeholders::_1));
  goal_sub_ = this->create_subscription<geometry_msgs::msg::PoseStamped>(
    "/move_base_simple/goal", rclcpp::QoS(1),
    std::bind(&GoalStateMachine::goalCallback, this, std::placeholders::_1));

  plan_client_ = this->create_client<srv::PlanPath>(plan_service_name_);

  RCLCPP_INFO(this->get_logger(), "Goal state machine started, service: %s", plan_service_name_.c_str());
}

void GoalStateMachine::goalCallback(const geometry_msgs::msg::PoseStamped::SharedPtr goal)
{
  // 将目标转换到地图坐标系（map_frame_），以便后续比较和调用规划服务
  geometry_msgs::msg::PoseStamped map_goal;
  if (goal->header.frame_id.empty() || goal->header.frame_id == map_frame_) {
    // 目标已经在地图坐标系或未指定框架，直接使用并设置为 map_frame_
    map_goal = *goal;
    map_goal.header.frame_id = map_frame_;
  } else {
    try {
      // 尝试通过 TF 将目标从其原始坐标系转换到地图坐标系
      const geometry_msgs::msg::TransformStamped tf_stamped = tf_buffer_->lookupTransform(
        map_frame_, goal->header.frame_id, tf2::TimePointZero, tf2::durationFromSec(0.2));
      tf2::doTransform(*goal, map_goal, tf_stamped);
    } catch (const tf2::TransformException & ex) {
      // 转换失败则记录警告并忽略该目标
      RCLCPP_WARN_THROTTLE(
        this->get_logger(), *this->get_clock(), 2000, "Goal transform failed: %s", ex.what());
      return;
    }
  }

  // 存储最新目标并标记为存在
  last_goal_ = map_goal;
  have_goal_ = true;
}

void GoalStateMachine::arriveCallback(const std_msgs::msg::Empty::SharedPtr msg)
{
  (void)msg;

  if (!have_goal_) {
    RCLCPP_WARN_THROTTLE(
      this->get_logger(), *this->get_clock(), 2000,
      "Arrival received without a stored goal.");
    return;
  }

  // 收到到达通知后，首先通过 TF 获取当前机器人在地图下的位姿
  geometry_msgs::msg::PoseStamped current_pose;
  if (!getRobotPose(current_pose)) {
    // 无法获取机器人位姿则放弃此次处理
    return;
  }

  // 计算机器人与目标之间的平面距离
  const double dx = last_goal_.pose.position.x - current_pose.pose.position.x;
  const double dy = last_goal_.pose.position.y - current_pose.pose.position.y;
  const double distance = std::hypot(dx, dy);

  // 如果在容忍范围内则无需重新规划
  if (distance <= goal_tolerance_) {
    RCLCPP_INFO(this->get_logger(), "Robot is within %.2f m of goal.", goal_tolerance_);
    return;
  }

  // 尝试调用规划服务进行重规划
  if (!plan_client_->wait_for_service(std::chrono::milliseconds(500))) {
    RCLCPP_WARN(this->get_logger(), "Plan service unavailable.");
    return;
  }

  auto req = std::make_shared<srv::PlanPath::Request>();
  req->goal = last_goal_;

  // 异步调用并在这里阻塞直到结果或超时
  auto future = plan_client_->async_send_request(req);
  if (rclcpp::spin_until_future_complete(this->get_node_base_interface(), future) ==
    rclcpp::FutureReturnCode::SUCCESS)
  {
    RCLCPP_INFO(
      this->get_logger(), "Requested replanning toward goal (distance %.2f m).", distance);
  } else {
    RCLCPP_WARN(this->get_logger(), "Failed to call plan service.");
  }
}

bool GoalStateMachine::getRobotPose(geometry_msgs::msg::PoseStamped & pose) const
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
    // TF 查询失败时记录警告并返回 false，上层调用决定如何处理
    RCLCPP_WARN(this->get_logger(), "TF lookup failed: %s", ex.what());
    return false;
  }
}

}  // namespace diablo_odin_mapplanner

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<diablo_odin_mapplanner::GoalStateMachine>());
  rclcpp::shutdown();
  return 0;
}
