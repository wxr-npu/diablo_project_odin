#include <algorithm>
#include <limits>
#include <memory>
#include <string>
#include <vector>

#include <pcl/io/pcd_io.h>
#include <pcl/point_cloud.h>
#include <pcl/point_types.h>

#include <nav_msgs/msg/occupancy_grid.hpp>
#include <rclcpp/rclcpp.hpp>

class Pcd2PgmRos2Node : public rclcpp::Node {
public:
  Pcd2PgmRos2Node() : Node("pcd2pgm_ros2_node") {
    pcd_file_ = this->declare_parameter<std::string>("pcd_file", "");
    frame_id_ = this->declare_parameter<std::string>("frame_id", "map");
    resolution_ = this->declare_parameter<double>("resolution", 0.05);
    min_height_ = this->declare_parameter<double>("min_height", -0.1);
    max_height_ = this->declare_parameter<double>("max_height", 0.1);
    publish_rate_ = this->declare_parameter<double>("publish_rate", 1.0);

    if (pcd_file_.empty()) {
      RCLCPP_FATAL(this->get_logger(), "Parameter 'pcd_file' is empty");
      throw std::runtime_error("pcd_file is required");
    }

    cloud_.reset(new pcl::PointCloud<pcl::PointXYZ>());
    if (pcl::io::loadPCDFile<pcl::PointXYZ>(pcd_file_, *cloud_) != 0) {
      RCLCPP_FATAL(this->get_logger(), "Failed to load PCD: %s", pcd_file_.c_str());
      throw std::runtime_error("load pcd failed");
    }

    createGridMap();

    auto qos = rclcpp::QoS(rclcpp::KeepLast(1)).reliable().transient_local();
    map_pub_ = this->create_publisher<nav_msgs::msg::OccupancyGrid>("/map", qos);

    const auto period = std::chrono::duration<double>(1.0 / std::max(0.1, publish_rate_));
    timer_ = this->create_wall_timer(
        std::chrono::duration_cast<std::chrono::milliseconds>(period),
        std::bind(&Pcd2PgmRos2Node::publishMap, this));

    RCLCPP_INFO(this->get_logger(), "Loaded PCD: %s, points=%zu", pcd_file_.c_str(), cloud_->size());
    RCLCPP_INFO(this->get_logger(), "Publishing /map at %.2f Hz", publish_rate_);
  }

private:
  void createGridMap() {
    if (cloud_->empty()) {
      throw std::runtime_error("pcd is empty");
    }

    float min_x = std::numeric_limits<float>::max();
    float max_x = std::numeric_limits<float>::lowest();
    float min_y = std::numeric_limits<float>::max();
    float max_y = std::numeric_limits<float>::lowest();

    for (const auto &pt : cloud_->points) {
      min_x = std::min(min_x, pt.x);
      max_x = std::max(max_x, pt.x);
      min_y = std::min(min_y, pt.y);
      max_y = std::max(max_y, pt.y);
    }

    const float padding = 1.0f;
    min_x -= padding;
    min_y -= padding;
    max_x += padding;
    max_y += padding;

    const int width = static_cast<int>((max_x - min_x) / resolution_) + 1;
    const int height = static_cast<int>((max_y - min_y) / resolution_) + 1;

    map_.header.frame_id = frame_id_;
    map_.info.resolution = static_cast<float>(resolution_);
    map_.info.width = static_cast<uint32_t>(width);
    map_.info.height = static_cast<uint32_t>(height);
    map_.info.origin.position.x = min_x;
    map_.info.origin.position.y = min_y;
    map_.info.origin.position.z = 0.0;
    map_.info.origin.orientation.w = 1.0;
    map_.data.assign(width * height, -1);

    std::vector<std::vector<bool>> has_point(height, std::vector<bool>(width, false));
    std::vector<std::vector<bool>> occupied(height, std::vector<bool>(width, false));

    for (const auto &pt : cloud_->points) {
      const int gx = static_cast<int>((pt.x - min_x) / resolution_);
      const int gy = static_cast<int>((pt.y - min_y) / resolution_);
      if (gx >= 0 && gx < width && gy >= 0 && gy < height) {
        has_point[gy][gx] = true;
        if (pt.z >= min_height_ && pt.z <= max_height_) {
          occupied[gy][gx] = true;
        }
      }
    }

    for (int y = 0; y < height; ++y) {
      for (int x = 0; x < width; ++x) {
        const int idx = y * width + x;
        if (occupied[y][x]) {
          map_.data[idx] = 100;
        } else if (has_point[y][x]) {
          map_.data[idx] = 0;
        } else {
          map_.data[idx] = -1;
        }
      }
    }
  }

  void publishMap() {
    map_.header.stamp = this->now();
    map_pub_->publish(map_);
  }

  std::string pcd_file_;
  std::string frame_id_;
  double resolution_;
  double min_height_;
  double max_height_;
  double publish_rate_;

  pcl::PointCloud<pcl::PointXYZ>::Ptr cloud_;
  nav_msgs::msg::OccupancyGrid map_;

  rclcpp::Publisher<nav_msgs::msg::OccupancyGrid>::SharedPtr map_pub_;
  rclcpp::TimerBase::SharedPtr timer_;
};

int main(int argc, char **argv) {
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<Pcd2PgmRos2Node>());
  rclcpp::shutdown();
  return 0;
}
