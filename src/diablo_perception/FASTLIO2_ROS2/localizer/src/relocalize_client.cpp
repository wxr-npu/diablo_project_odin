#include <string>
#include <chrono>
#include <rclcpp/rclcpp.hpp>
#include <interface/srv/relocalize.hpp>
#include <geometry_msgs/msg/pose_with_covariance_stamped.hpp>
#include <tf2_geometry_msgs/tf2_geometry_msgs.h>

using namespace std::chrono_literals;

class RelocalizeClient : public rclcpp::Node
{
public:
  RelocalizeClient() : Node("relocalize_client")
  {

    this->declare_parameter("pcd_file", "map.pcd");
    pcd_file_ = this->get_parameter("pcd_file").as_string();

    // 创建服务客户端
    client_ = this->create_client<interface::srv::Relocalize>("/localizer/relocalize");

    // 创建订阅者，订阅 /initpose 话题
    subscription_ = this->create_subscription<geometry_msgs::msg::PoseWithCovarianceStamped>(
      "/initialpose", 10, std::bind(&RelocalizeClient::topic_callback, this, std::placeholders::_1));

    // 等待服务可用
    while (!client_->wait_for_service(1s)) {
      if (!rclcpp::ok()) {
        RCLCPP_ERROR(this->get_logger(), "Interrupted while waiting for the service. Exiting.");
        return;
      }
      RCLCPP_INFO(this->get_logger(), "Waiting for service...");
    }
    RCLCPP_INFO(this->get_logger(), "Service is available, you can Click Pose with 2D Pose Estimate in Rviz2 now.");
  }

private:
  void topic_callback(const geometry_msgs::msg::PoseWithCovarianceStamped::SharedPtr msg)
  {
    // 获取位姿信息
    RCLCPP_INFO(this->get_logger(), "Received pose: x=%f, y=%f, z=%f", msg->pose.pose.position.x, msg->pose.pose.position.y, msg->pose.pose.position.z);
    geometry_msgs::msg::PoseWithCovariance pose = msg->pose; 
    x_ = pose.pose.position.x;
    y_ = pose.pose.position.y;
    z_ = pose.pose.position.z;

    // 将四元数转换为欧拉角 (需要包含 tf2_geometry_msgs 头文件)
    tf2::Quaternion q(
      pose.pose.orientation.x,
      pose.pose.orientation.y,
      pose.pose.orientation.z,
      pose.pose.orientation.w);
    tf2::Matrix3x3 m(q);
    m.getRPY(roll_, pitch_, yaw_);

    // 调用服务
    call_service();
  }

  void call_service()
  {
    RCLCPP_INFO(this->get_logger(), "Calling Relocalize service...");
    auto request = std::make_shared<interface::srv::Relocalize::Request>();
    // 设置请求参数
    request->pcd_path = pcd_file_; // 从外部设置或使用默认值
    pcd_file_ = "";
    request->x = x_;
    request->y = y_;
    request->z = z_;
    request->yaw = yaw_;
    request->pitch = pitch_;
    request->roll = roll_;

    // 等待服务响应
    while (!client_->wait_for_service(1s)) {
      if (!rclcpp::ok()) {
        RCLCPP_ERROR(this->get_logger(), "Interrupted while waiting for the service. Exiting.");
        return;
      }
      RCLCPP_INFO(this->get_logger(), "Service not available, waiting again...");
    }
    auto result = client_->async_send_request(request);
	//以下代码会报错
    // Error: terminate called after throwing an instance of 'std::runtime_error'
	// if (rclcpp::spin_until_future_complete(this->get_node_base_interface(), result) == rclcpp::FutureReturnCode::SUCCESS){
	// 	RCLCPP_INFO(this->get_logger(), "Relocalization service called successfully.");
	// 	RCLCPP_INFO(this->get_logger(), "Result: %s", result.get()->message.c_str());
	// }
	// else {
	// 	RCLCPP_ERROR(this->get_logger(), "Failed to call service");
	// }

    auto future_result = client_->async_send_request(request, std::bind(&RelocalizeClient::future_callback, this, std::placeholders::_1));
  }

  void future_callback(rclcpp::Client<interface::srv::Relocalize>::SharedFuture future) {
    if (future.wait_for(std::chrono::seconds(0)) == std::future_status::ready){
        auto result = future.get();
        RCLCPP_INFO(this->get_logger(), "Relocalization service called successfully.");
        RCLCPP_INFO(this->get_logger(), "Result: %s", result->message.c_str());
    } else {
        RCLCPP_ERROR(this->get_logger(), "Failed to call service");
    }
  }

  rclcpp::Client<interface::srv::Relocalize>::SharedPtr client_;
  rclcpp::Subscription<geometry_msgs::msg::PoseWithCovarianceStamped>::SharedPtr subscription_;
  double x_ = 0.0;
  double y_ = 0.0;
  double z_ = 0.0;
  double yaw_ = 0.0;
  double pitch_ = 0.0;
  double roll_ = 0.0;
  std::string pcd_file_ = " ";
};

int main(int argc, char * argv[])
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<RelocalizeClient>());
  rclcpp::shutdown();
  return 0;
}