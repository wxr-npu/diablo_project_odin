#include "rclcpp/rclcpp.hpp"
#include "motion_msgs/msg/motion_ctrl.hpp"
#include "geometry_msgs/msg/twist.hpp"

class MsgConvert : public rclcpp::Node
{
public:

  MsgConvert() : Node("msg_convert")
  {
    // 创建一个发布器来发布自定义消息
    motion_cmd_pub = this->create_publisher<motion_msgs::msg::MotionCtrl>("diablo/MotionCmd", 10);
    // 创建一个订阅器来订阅cmd_vel消息
    cmd_vel_sub = 
      this->create_subscription<geometry_msgs::msg::Twist>("cmd_vel", 10, std::bind(&MsgConvert::msgconvert_callback, this, std::placeholders::_1));
    //创建一个节点接收键盘控制的消息
    teleop_cmd_sub = 
      this->create_subscription<motion_msgs::msg::MotionCtrl>("key_control", 10, std::bind(&MsgConvert::key_control_callback, this, std::placeholders::_1));
    //创建一个定时器每隔50ms(20hz)发布一次速度信息
    timer = this->create_wall_timer(std::chrono::milliseconds(50), std::bind(&MsgConvert::timer_callback, this));
    
  
  }

private:
  motion_msgs::msg::MotionCtrl vel_msg;
  motion_msgs::msg::MotionCtrl key_msg;

  void msgconvert_callback(const geometry_msgs::msg::Twist::SharedPtr msg)
  {
    // 将传进来的cmd_vel速度信息赋值给自定义消息
    vel_msg.value.forward = msg->linear.x;
    vel_msg.value.left = msg->angular.z;
    RCLCPP_INFO(this->get_logger(), "start cmd_vel -> motion_msgs");
  }

  //接收键盘的回调消息
  void key_control_callback(const motion_msgs::msg::MotionCtrl::SharedPtr msg)
  {
    key_msg.value = msg->value;
    key_msg.mode = msg->mode;
    key_msg.mode_mark = msg->mode_mark;
    key_msg.emergency_mode = msg->emergency_mode;
    
  }

  void timer_callback()
  {
    
    if (!key_msg.emergency_mode)//判断当前是否为紧急模式
    {
      if(vel_msg.value.forward != 0.0 || vel_msg.value.left != 0.0)//导航模式下只发布cmd_vel的速度消息，其它模式与键盘设置后的机器人姿态保持一致
      {
        vel_msg.value.up = key_msg.value.up;
        vel_msg.value.pitch = key_msg.value.pitch;
        vel_msg.mode_mark = key_msg.mode_mark;
        vel_msg.mode = key_msg.mode;
        vel_msg.emergency_mode = key_msg.emergency_mode;
        motion_cmd_pub->publish(vel_msg);
      }
      else
      {
        motion_cmd_pub->publish(key_msg);
      }
        
      
    }
    else//紧急模式下只可用键盘控制发布消息
    {
      motion_cmd_pub->publish(key_msg);
      
    }
    
    
  }
  rclcpp::Publisher<motion_msgs::msg::MotionCtrl>::SharedPtr motion_cmd_pub;
  rclcpp::Subscription<motion_msgs::msg::MotionCtrl>::SharedPtr teleop_cmd_sub;
  rclcpp::Subscription<geometry_msgs::msg::Twist>::SharedPtr cmd_vel_sub;
  rclcpp::TimerBase::SharedPtr timer; 
} ;

int main(int argc, char** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<MsgConvert>());
  rclcpp::shutdown();
  return 0;
}