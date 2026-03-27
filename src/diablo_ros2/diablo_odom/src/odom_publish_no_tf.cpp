#include "rclcpp/rclcpp.hpp"
#include "rclcpp/time.hpp"
#include "motion_msgs/msg/leg_motors.hpp"
#include "nav_msgs/msg/odometry.hpp"
#include "tf2_msgs/msg/tf_message.hpp"
#include "tf2_ros/transform_broadcaster.h"
#include "tf2/LinearMath/Quaternion.h"

using namespace std::chrono_literals;

class OdomPublisherNode: public rclcpp::Node
{
public:
  OdomPublisherNode()
  : Node("odom_publish_node")
  , x(0.0)
  , y(0.0)
  , theta(0.0)
  , wheel_radius(0.09)
  , wheel_separation(0.488)
  , timestamp(this->get_clock()->now())
  {
    // subscrible left and right vel of wheel, calc odom diff
    motor_subscriber_ = this->create_subscription<motion_msgs::msg::LegMotors>(
        "/diablo/sensor/Motors", 10, std::bind(&OdomPublisherNode::legMotorsCallback, this, std::placeholders::_1));
    
    // create odom and tf publisher
    odom_publisher_ = this->create_publisher<nav_msgs::msg::Odometry>("/diablo_odom", 10);
    // tf_publisher_ = this->create_publisher<tf2_msgs::msg::TFMessage>("/tf", 10);

    // Initialize the odometry message
    odom_msg_.header.frame_id = "odom";
    odom_msg_.child_frame_id = "base_footprint";
  }

private:
  void legMotorsCallback(const motion_msgs::msg::LegMotors::SharedPtr msg)
  {
    rclcpp::Time current_time = this->get_clock()->now();

    // odom calc
    const double dt = current_time.seconds() - timestamp.seconds();
    const double left_vel = msg->left_wheel_vel * wheel_radius;
    const double right_vel = msg->right_wheel_vel * wheel_radius;
    const double v = (left_vel + right_vel) * 0.5;
    const double w = (right_vel - left_vel) / wheel_separation;
    theta += w * dt;
    x += v * dt * cos(theta);
    y += v * dt * sin(theta);

    // Update the odometry message
    odom_msg_.header.stamp = this->get_clock()->now();
    odom_msg_.pose.pose.position.x = x;
    odom_msg_.pose.pose.position.y = y;
    odom_msg_.pose.pose.position.z = 0;

    tf2::Quaternion q;
    q.setRPY(0, 0, theta);

    odom_msg_.pose.pose.orientation.x = q.x();
    odom_msg_.pose.pose.orientation.y = q.y();
    odom_msg_.pose.pose.orientation.z = q.z();
    odom_msg_.pose.pose.orientation.w = q.w();

    odom_msg_.twist.twist.linear.x = v;
    odom_msg_.twist.twist.angular.z = w;

    // Update the tf message
    // tf_msg_.transforms.resize(1);
    // tf_msg_.transforms[0].header.stamp = this->get_clock()->now();
    // tf_msg_.transforms[0].header.frame_id = odom_msg_.header.frame_id;
    // tf_msg_.transforms[0].child_frame_id = odom_msg_.child_frame_id;
    // tf_msg_.transforms[0].transform.translation.x = x;
    // tf_msg_.transforms[0].transform.translation.y = y;

    // // tf message
    // tf_msg_.transforms[0].transform.rotation.x = q.x();
    // tf_msg_.transforms[0].transform.rotation.y = q.y();
    // tf_msg_.transforms[0].transform.rotation.z = q.z();
    // tf_msg_.transforms[0].transform.rotation.w = q.w();

    // Publish odom and tf message
    odom_publisher_->publish(odom_msg_);
    // tf_publisher_->publish(tf_msg_);

    timestamp = current_time;
  }

  rclcpp::Subscription<motion_msgs::msg::LegMotors>::SharedPtr motor_subscriber_;
  rclcpp::Publisher<nav_msgs::msg::Odometry>::SharedPtr odom_publisher_;
  // rclcpp::Publisher<tf2_msgs::msg::TFMessage>::SharedPtr tf_publisher_;
  rclcpp::TimerBase::SharedPtr timer_;
  nav_msgs::msg::Odometry odom_msg_;
  tf2_msgs::msg::TFMessage tf_msg_;

  double x, y, theta;
  double wheel_radius, wheel_separation;
  rclcpp::Time timestamp;
};

int main(int argc, char** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<OdomPublisherNode>());
  rclcpp::shutdown();
  return 0;
}