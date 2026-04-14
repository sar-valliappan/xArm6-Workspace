# xArm6 ROS 2 Simulation (macOS Apple Silicon)

This workspace runs xArm6 with ROS 2 Humble, MoveIt 2, and browser-based desktop access through Docker.

## Quick Start

Run these from the workspace root:

  cd /Users/svalliappan/xarm6_ws
  chmod +x build.sh start.sh && ./build.sh
  ./start.sh

Open in browser:

  http://localhost:6080/vnc.html?autoconnect=1&resize=remote

## What you get

- ROS 2 Humble toolchain in Docker
- xArm ROS 2 packages
- MoveIt 2 planning setup
- Browser desktop at http://localhost:6080

## Prerequisites

Install on host macOS:

1. Docker Desktop (Apple Silicon)
2. Git
3. Optional: VS Code

Recommended Docker resources:

- Memory: 8 GB minimum, 12 to 16 GB preferred
- CPU: 4 cores minimum

## Repository scripts

- build.sh: one-time setup and build
- start.sh: run simulation desktop and launch stack

## First-time installation

From the workspace root:

  cd /Users/svalliappan/xarm6_ws
  chmod +x build.sh start.sh
  ./build.sh

What build.sh does:

1. Clones xarm_ros2 into src/xarm_ros2 if missing
2. Builds Docker image xarm6_sim
3. Applies ARM64-compatible xarm_gazebo patch
4. Runs rosdep install in container
5. Builds workspace with colcon

## Run the system

From the workspace root:

  cd /Users/svalliappan/xarm6_ws
  ./start.sh

Then open in browser:

  http://localhost:6080/vnc.html?autoconnect=1&resize=remote

Notes:

- start.sh currently defaults to fake mode for stability on ARM64
- This keeps desktop and MoveIt workflow reliable on macOS

## Optional: force Gazebo mode

Gazebo mode may crash on some ARM64 environments due to gz_ros2_control runtime issues.

  cd /Users/svalliappan/xarm6_ws
  XARM_SIM_MODE=gazebo ./start.sh

If Gazebo mode is unstable, use default fake mode.

## Daily workflow

1. Start Docker Desktop
2. Run start.sh
3. Open browser URL above
4. Stop with Ctrl+C in terminal

## Troubleshooting

### localhost:6080 does not open

Run:

  docker ps --format 'table {{.ID}}\t{{.Names}}\t{{.Ports}}'

You should see container port mapping 0.0.0.0:6080->6080/tcp.

If another stale run is holding ports:

  docker ps -q --filter "name=xarm6_ws-xarm6_sim-run" | xargs -I {} docker stop {}

Then restart:

  ./start.sh

### Build fails in colcon

The workspace is configured to build without symlink install to avoid bind-mount symlink issues on macOS Docker.
If needed, clean and rebuild from host:

  rm -rf build install log
  ./build.sh

### Rebuild image after Dockerfile changes

  docker compose build xarm6_sim

### Check noVNC endpoint from terminal

  curl -I http://localhost:6080/vnc.html

Expected response includes HTTP/1.1 200 OK.

**"No such package" errors**
- Make sure you cloned with --recursive: `git submodule update --init --recursive`

---

## Architecture Notes (why it's set up this way)

| Problem | Cause | Solution used |
|---|---|---|
| Classic Gazebo missing | `ros-humble-gazebo-ros` has no ARM64 apt package | Ignition Fortress + ros_gz bridge |
| RViz crashes (GLXContext) | XQuartz on macOS can't provide OpenGL 3.3 | VNC desktop with Mesa software rendering |
| move_group segfault | ARM64 bug in rclcpp CallbackGroup destructor | `LD_PRELOAD=libatomic.so.1` |
| chown permission errors | Git pack files cloned as root | `|| true` in setup.sh, fix ownership before clone |

---

## Software Versions

| Software | Version |
|---|---|
| ROS 2 | Humble Hawksbill (Ubuntu 22.04) |
| MoveIt 2 | 2.5.x |
| Gazebo | Ignition Fortress |
| Docker base image | ros:humble |
| VNC | TigerVNC |
| noVNC | latest apt |
