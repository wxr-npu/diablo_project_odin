#include <filesystem>
#include <memory>
#include <mutex>
#include <string>

#include <pcl/filters/statistical_outlier_removal.h>
#include <pcl/filters/voxel_grid.h>
#include <pcl/io/pcd_io.h>
#include <pcl/point_cloud.h>
#include <pcl/point_types.h>
#include <pcl_conversions/pcl_conversions.h>

#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/point_cloud2.hpp>
#include <std_srvs/srv/trigger.hpp>

class PointCloudSaverRos2Node : public rclcpp::Node {
public:
  PointCloudSaverRos2Node() : Node("pointcloud_saver") {
    cloud_topic_ = this->declare_parameter<std::string>("cloud_topic", "/odin1/cloud_slam");
    output_file_ = this->declare_parameter<std::string>("output_file", "map.pcd");
    max_points_ = this->declare_parameter<int>("max_points", 10000000);
    voxel_size_ = this->declare_parameter<double>("voxel_size", 0.05);
    apply_statistical_filter_ = this->declare_parameter<bool>("apply_statistical_filter", true);
    mean_k_ = this->declare_parameter<int>("sor_mean_k", 20);
    stddev_mul_thresh_ = this->declare_parameter<double>("sor_stddev_mul_thresh", 1.0);

    cloud_.reset(new pcl::PointCloud<pcl::PointXYZ>());

    sub_ = this->create_subscription<sensor_msgs::msg::PointCloud2>(
        cloud_topic_, rclcpp::SensorDataQoS(),
        std::bind(&PointCloudSaverRos2Node::cloudCallback, this, std::placeholders::_1));

    start_srv_ = this->create_service<std_srvs::srv::Trigger>(
        "start_recording", std::bind(&PointCloudSaverRos2Node::startRecording, this,
                                      std::placeholders::_1, std::placeholders::_2));
    stop_srv_ = this->create_service<std_srvs::srv::Trigger>(
        "stop_recording", std::bind(&PointCloudSaverRos2Node::stopRecording, this,
                                     std::placeholders::_1, std::placeholders::_2));
    save_srv_ = this->create_service<std_srvs::srv::Trigger>(
        "save_map", std::bind(&PointCloudSaverRos2Node::saveMap, this,
                               std::placeholders::_1, std::placeholders::_2));
    clear_srv_ = this->create_service<std_srvs::srv::Trigger>(
        "clear_map", std::bind(&PointCloudSaverRos2Node::clearMap, this,
                                std::placeholders::_1, std::placeholders::_2));

    RCLCPP_INFO(this->get_logger(), "pointcloud_saver_ros2_node started");
    RCLCPP_INFO(this->get_logger(), "cloud_topic: %s", cloud_topic_.c_str());
    RCLCPP_INFO(this->get_logger(), "output_file: %s", output_file_.c_str());
  }

private:
  void cloudCallback(const sensor_msgs::msg::PointCloud2::SharedPtr msg) {
    if (!recording_) {
      return;
    }

    pcl::PointCloud<pcl::PointXYZ> incoming;
    pcl::fromROSMsg(*msg, incoming);

    if (incoming.empty()) {
      return;
    }

    std::lock_guard<std::mutex> lock(mutex_);
    if (static_cast<int>(cloud_->size()) >= max_points_) {
      return;
    }

    if (static_cast<int>(cloud_->size() + incoming.size()) > max_points_) {
      const auto allowed = static_cast<size_t>(max_points_ - cloud_->size());
      cloud_->points.insert(cloud_->points.end(), incoming.points.begin(), incoming.points.begin() + allowed);
    } else {
      cloud_->points.insert(cloud_->points.end(), incoming.points.begin(), incoming.points.end());
    }

    cloud_->width = cloud_->points.size();
    cloud_->height = 1;
    cloud_->is_dense = false;
  }

  void startRecording(const std::shared_ptr<std_srvs::srv::Trigger::Request> /*request*/,
                      std::shared_ptr<std_srvs::srv::Trigger::Response> response) {
    recording_ = true;
    response->success = true;
    response->message = "start_recording ok";
    RCLCPP_INFO(this->get_logger(), "Start recording point cloud");
  }

  void stopRecording(const std::shared_ptr<std_srvs::srv::Trigger::Request> /*request*/,
                     std::shared_ptr<std_srvs::srv::Trigger::Response> response) {
    recording_ = false;
    response->success = true;
    response->message = "stop_recording ok";
    RCLCPP_INFO(this->get_logger(), "Stop recording point cloud");
  }

  void clearMap(const std::shared_ptr<std_srvs::srv::Trigger::Request> /*request*/,
                std::shared_ptr<std_srvs::srv::Trigger::Response> response) {
    std::lock_guard<std::mutex> lock(mutex_);
    cloud_->clear();
    cloud_->width = 0;
    cloud_->height = 1;
    cloud_->is_dense = false;
    response->success = true;
    response->message = "clear_map ok";
    RCLCPP_INFO(this->get_logger(), "Cleared accumulated cloud");
  }

  void saveMap(const std::shared_ptr<std_srvs::srv::Trigger::Request> /*request*/,
               std::shared_ptr<std_srvs::srv::Trigger::Response> response) {
    std::string output_file;
    double voxel_size = 0.0;
    bool apply_filter = false;
    int mean_k = 20;
    double stddev_mul = 1.0;

    this->get_parameter("output_file", output_file);
    this->get_parameter("voxel_size", voxel_size);
    this->get_parameter("apply_statistical_filter", apply_filter);
    this->get_parameter("sor_mean_k", mean_k);
    this->get_parameter("sor_stddev_mul_thresh", stddev_mul);

    pcl::PointCloud<pcl::PointXYZ>::Ptr snapshot(new pcl::PointCloud<pcl::PointXYZ>());
    {
      std::lock_guard<std::mutex> lock(mutex_);
      *snapshot = *cloud_;
    }

    if (snapshot->empty()) {
      response->success = false;
      response->message = "cloud is empty";
      return;
    }

    pcl::PointCloud<pcl::PointXYZ>::Ptr processed(new pcl::PointCloud<pcl::PointXYZ>());
    *processed = *snapshot;

    if (voxel_size > 0.0) {
      pcl::VoxelGrid<pcl::PointXYZ> voxel;
      voxel.setInputCloud(processed);
      voxel.setLeafSize(static_cast<float>(voxel_size), static_cast<float>(voxel_size),
                        static_cast<float>(voxel_size));
      pcl::PointCloud<pcl::PointXYZ>::Ptr voxel_cloud(new pcl::PointCloud<pcl::PointXYZ>());
      voxel.filter(*voxel_cloud);
      processed = voxel_cloud;
    }

    if (apply_filter && processed->size() >= static_cast<size_t>(mean_k + 1)) {
      pcl::StatisticalOutlierRemoval<pcl::PointXYZ> sor;
      sor.setInputCloud(processed);
      sor.setMeanK(mean_k);
      sor.setStddevMulThresh(stddev_mul);
      pcl::PointCloud<pcl::PointXYZ>::Ptr filtered(new pcl::PointCloud<pcl::PointXYZ>());
      sor.filter(*filtered);
      processed = filtered;
    }

    const std::filesystem::path output_path(output_file);
    std::filesystem::create_directories(output_path.parent_path());

    const int ret = pcl::io::savePCDFileBinary(output_file, *processed);
    if (ret != 0) {
      response->success = false;
      response->message = "failed to save pcd";
      return;
    }

    response->success = true;
    response->message = "saved: " + output_file;
    RCLCPP_INFO(this->get_logger(), "Saved PCD: %s (points=%zu)", output_file.c_str(),
                processed->size());
  }

  std::string cloud_topic_;
  std::string output_file_;
  int max_points_;
  double voxel_size_;
  bool apply_statistical_filter_;
  int mean_k_;
  double stddev_mul_thresh_;

  bool recording_ = false;
  std::mutex mutex_;
  pcl::PointCloud<pcl::PointXYZ>::Ptr cloud_;

  rclcpp::Subscription<sensor_msgs::msg::PointCloud2>::SharedPtr sub_;
  rclcpp::Service<std_srvs::srv::Trigger>::SharedPtr start_srv_;
  rclcpp::Service<std_srvs::srv::Trigger>::SharedPtr stop_srv_;
  rclcpp::Service<std_srvs::srv::Trigger>::SharedPtr save_srv_;
  rclcpp::Service<std_srvs::srv::Trigger>::SharedPtr clear_srv_;
};

int main(int argc, char **argv) {
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<PointCloudSaverRos2Node>());
  rclcpp::shutdown();
  return 0;
}
