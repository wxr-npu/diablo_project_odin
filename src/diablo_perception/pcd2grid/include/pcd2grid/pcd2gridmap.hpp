/*
Pcd2GridMap (Author: sujit-168)
Convert a .pcd file to a gridmap and publish it as a nav_msgs::OccupancyGrid message.
*/

#include <iostream>
#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/point_cloud2.hpp"
#include "nav_msgs/msg/occupancy_grid.hpp"
#include <pcl_conversions/pcl_conversions.h>
#include <pcl/point_cloud.h>
#include <pcl/point_types.h>

class Pcd2GridMap : public rclcpp::Node {
private:
    double resolution;
    double min_z, max_z;
    std::string frame_id;
    std::string pcd_file;
    std::string map_topic;

    rclcpp::Publisher<nav_msgs::msg::OccupancyGrid>::SharedPtr gridmap_pub; // Publisher for the gridmap
    
    void load_pcd(const std::string &file, pcl::PointCloud<pcl::PointXYZ>::Ptr &cloud);
    void cloud2gridmap(const pcl::PointCloud<pcl::PointXYZ>::Ptr &cloud, nav_msgs::msg::OccupancyGrid &gridmap);
    void publish_gridmap(const nav_msgs::msg::OccupancyGrid &gridmap);

public:
    explicit Pcd2GridMap(std::string name);
    ~Pcd2GridMap();
    void run();
};