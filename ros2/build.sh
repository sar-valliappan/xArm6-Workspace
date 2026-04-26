#!/bin/bash
# =============================================================================
# xArm6 First-Time Build Script
# Run this once after cloning. Builds the Docker image and ROS workspace.
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "=============================================="
echo "  xArm6 — First Time Setup"
echo "=============================================="
echo ""

# Step 1: Clone xarm_ros2 if not already present
if [ ! -d "src/xarm_ros2" ]; then
    echo "--> Cloning xarm_ros2..."
    mkdir -p src
    git clone https://github.com/xArm-Developer/xarm_ros2.git \
        --recursive -b humble src/xarm_ros2
    sudo chown -R $(whoami) src/xarm_ros2/.git
else
    echo "--> src/xarm_ros2 already exists, skipping clone."
fi

# Step 2: Build the Docker image
echo ""
echo "--> Building Docker image (this takes 15-20 min the first time)..."
docker compose build

# Step 3: Patch xarm_gazebo to use Ignition Fortress instead of classic Gazebo
echo ""
echo "--> Patching xarm_gazebo for Ignition Fortress (ARM64)..."

cat > src/xarm_ros2/xarm_gazebo/CMakeLists.txt << 'EOF'
cmake_minimum_required(VERSION 3.5)
project(xarm_gazebo)

find_package(ament_cmake REQUIRED)
find_package(ros_gz_sim REQUIRED)
find_package(ros_gz_bridge REQUIRED)
find_package(xarm_description REQUIRED)
find_package(xarm_controller REQUIRED)

install(
  DIRECTORY launch worlds
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
EOF

cat > src/xarm_ros2/xarm_gazebo/package.xml << 'EOF'
<?xml version="1.0"?>
<package format="3">
  <name>xarm_gazebo</name>
  <version>0.0.1</version>
  <description>xarm gazebo simulation with Ignition Fortress</description>
  <maintainer email="support@ufactory.cc">UFACTORY</maintainer>
  <license>BSD</license>

  <buildtool_depend>ament_cmake</buildtool_depend>

  <depend>ros_gz_sim</depend>
  <depend>ros_gz_bridge</depend>
  <depend>xarm_description</depend>
  <depend>xarm_controller</depend>

  <export>
    <build_type>ament_cmake</build_type>
  </export>
</package>
EOF

# Step 4: Build the ROS 2 workspace inside the container
echo ""
echo "--> Building ROS 2 workspace..."
docker compose run --rm xarm6_sim bash -c '
    set -e
    cd /home/ws

    echo "--> Running rosdep..."
    export ROS_DISTRO=humble
    sudo rosdep fix-permissions
    sudo rosdep update
    sudo rosdep install \
        --from-paths src \
        --ignore-src \
        --rosdistro humble \
        -y \
        --skip-keys="gazebo_ros gazebo_plugins gazebo_ros2_control gazebo_ros_pkgs realsense_gazebo_plugin"

    echo "--> Running colcon build..."
    source /opt/ros/humble/setup.bash
    colcon build --symlink-install \
        --packages-ignore realsense_gazebo_plugin mbot_demo d435i_xarm_setup

    echo ""
    echo "Build complete!"
'

echo ""
echo "=============================================="
echo "  Setup complete!"
echo "  Run ./start.sh to launch the simulation."
echo "=============================================="
