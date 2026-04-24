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

## Real Hardware Run (xArm6)

For physical robot runs, use the dedicated safety launcher:

  cd /Users/svalliappan/xarm6_ws
  ROBOT_IP=192.168.1.240 XARM_PHYSICAL_CONFIRM=I_UNDERSTAND_RISKS ./start_real.sh

What `start_real.sh` does:

- Launches `xarm6_moveit_realmove.launch.py`
- Waits for arm/gripper trajectory action servers
- Requires explicit operator confirmation before running the demo node
- Enables physical safety interlock and step-by-step confirmation in the node

Optional flags:

- `XARM_ADD_GRIPPER=true|false` (default `true`)
- `XARM_STEP_CONFIRM=1|0` (default `1`, asks before each motion block)

## Run Demo Node (RViz)

The most reliable way on Apple Silicon is to run fake mode and launch the demo
inside the same simulation container.

From the workspace root:

  cd /Users/svalliappan/xarm6_ws
  XARM_RUN_DEMO=1 ./start.sh

To include the xArm gripper model and run open/close commands in the demo:

  cd /Users/svalliappan/xarm6_ws
  XARM_ADD_GRIPPER=true XARM_RUN_DEMO=1 ./start.sh

Then open in browser:

  http://localhost:6080/vnc.html?autoconnect=1&resize=remote

Current node behavior is intentionally minimal for safer bring-up:

- Open gripper
- Perform a very small joint-space move
- Close gripper lightly

With gripper enabled, the demo sends both open and close gripper commands.

Why this mode works:

- The controller action server runs in the same container session as the demo node
- Gazebo physics is optional and currently unstable on ARM64 in this stack

If you want to run the node manually (without auto-demo):

1. Start simulation:

     ./start.sh

2. In a second terminal, run:

     docker compose run --rm xarm6_sim bash -lc "cd /home/ws && source /opt/ros/humble/setup.bash && colcon build --packages-select xarm_pick_place && source install/setup.bash && ros2 run xarm_pick_place pick_place_node.py"

Note: launching the node in a separate one-off container may not always see the
live trajectory action server from the first container. Use XARM_RUN_DEMO=1 for
the most consistent behavior.

## Optional: force Gazebo mode

Gazebo mode may crash on some ARM64 environments due to gz_ros2_control runtime issues.

  cd /Users/svalliappan/xarm6_ws
  XARM_SIM_MODE=gazebo ./start.sh

If Gazebo mode is unstable, use default fake mode.

## Environment Flags

- XARM_SIM_MODE
  - fake (default): stable MoveIt/RViz test mode
  - gazebo: attempt Gazebo mode (may crash on Apple Silicon)
- XARM_RUN_DEMO
  - 0 (default): launch stack only
  - 1: auto-run demo node after startup
- XARM_ADD_GRIPPER
  - false (default): arm only
  - true: include standard xArm gripper model and controller

## Physical Machine Safety

The demo node includes a physical-mode interlock.
Use it only after verifying the robot is clear of obstacles and ready to move.

Before any motion on hardware, set:

  XARM_PHYSICAL_MODE=1
  XARM_PHYSICAL_CONFIRM=I_UNDERSTAND_RISKS

Recommended physical test command:

  XARM_PHYSICAL_MODE=1 XARM_PHYSICAL_CONFIRM=I_UNDERSTAND_RISKS XARM_ADD_GRIPPER=true XARM_RUN_DEMO=1 ./start.sh

Safety behavior in physical mode:

- Runs only a minimal sequence (open gripper, tiny move, close gripper)
- Refuses to move unless confirmation is provided explicitly
- Supports step-by-step operator confirmation when enabled
- Uses a light gripper close position instead of a full crush-close

Do not use Gazebo mode for the first physical test. Start in fake/RViz mode or
validate the node on the bench with the robot clear of objects and people.

Known limitation on Apple Silicon:

- Gazebo (gz) may start and then crash (segfault/exit 137) in this environment.
- RViz fake mode remains the recommended test path for motion validation.

## Direct SDK Script (Real Robot)

For direct xArm SDK testing outside ROS, use [simple_xarm_movements.py](simple_xarm_movements.py).
This script performs a simple Cartesian pick-and-place style sequence and then returns home.

Before running:

- Update the robot IP inside the script if needed.
- Ensure the workcell is clear and E-stop procedures are in place.

Run from workspace root:

  cd /Users/svalliappan/xarm6_ws
  python3 simple_xarm_movements.py

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
