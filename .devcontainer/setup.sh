#!/bin/bash
# postCreateCommand — runs once after the container is first created.
set -e

echo "==> Running rosdep update..."
sudo rosdep update

echo "==> Installing dependencies..."
sudo rosdep install \
    --from-paths src \
    --ignore-src \
    -y \
    --skip-keys="gazebo_ros gazebo_plugins gazebo_ros2_control gazebo_ros_pkgs realsense_gazebo_plugin"

echo "==> Fixing workspace ownership..."
sudo chown -R "$(whoami)" /home/ws/ 2>/dev/null || true

echo ""
echo "✓ Setup complete! Run 'start-vnc.sh' to start the desktop."
