# xArm6 Workspace

This workspace supports two independent workflows:

1. ROS 2 workflow (Docker-based): simulation, MoveIt, RViz, and ROS demos.
2. Python SDK workflow (no Docker required): direct robot control scripts.

## Do You Need Docker For Python SDK?

No. Docker is only required for the ROS 2 workflow.

Use Docker when you run ROS 2 tools and launch files.
Do not use Docker when running scripts in python_sdk.

## Repository Organization

### ROS 2 assets

- Location: ros2/
- ROS packages: ros2/src/xarm_ros2
- ROS launcher/build scripts: ros2/build.sh, ros2/start.sh, ros2/start_real.sh
- ROS container files: ros2/Dockerfile, ros2/docker-compose.yml
- ROS build artifacts: ros2/build, ros2/install, ros2/log

### Python SDK assets

- Scripts: python_sdk/simple_xarm_movements.py, python_sdk/xarm_torque_movements.py

---

## ROS 2 Section (Docker)

### Prerequisites

1. Docker Desktop (Apple Silicon)
2. Git
3. Optional: VS Code

Recommended Docker resources:

- Memory: 8 GB minimum, 12 to 16 GB preferred
- CPU: 4 cores minimum

### Installation

```bash
cd /Users/svalliappan/xarm6_ws
chmod +x ros2/build.sh ros2/start.sh ros2/start_real.sh
./ros2/build.sh
```

What build.sh does:

1. Clones xarm_ros2 into ros2/src/xarm_ros2 if missing.
2. Builds Docker image xarm6_sim.
3. Applies ARM64-compatible xarm_gazebo patch.
4. Runs rosdep install in container.
5. Builds the workspace with colcon.

### Execution

Start simulation (default fake mode):

```bash
cd /Users/svalliappan/xarm6_ws
./ros2/start.sh
```

Open browser desktop:

```text
http://localhost:6080/vnc.html?autoconnect=1&resize=remote
```

Auto-run ROS demo:

```bash
cd /Users/svalliappan/xarm6_ws
XARM_RUN_DEMO=1 ./ros2/start.sh
```

Enable gripper in demo:

```bash
cd /Users/svalliappan/xarm6_ws
XARM_ADD_GRIPPER=true XARM_RUN_DEMO=1 ./ros2/start.sh
```

Run real hardware launcher with safety confirmation:

```bash
cd /Users/svalliappan/xarm6_ws
ROBOT_IP=192.168.1.240 XARM_PHYSICAL_CONFIRM=I_UNDERSTAND_RISKS ./ros2/start_real.sh
```

### Environment flags

- XARM_SIM_MODE=fake|gazebo (default: fake)
- XARM_RUN_DEMO=0|1 (default: 0)
- XARM_ADD_GRIPPER=false|true (default: false)
- XARM_STEP_CONFIRM=1|0 (default in physical flow: 1)

### Troubleshooting

Check noVNC mapping:

```bash
docker ps --format 'table {{.ID}}\t{{.Names}}\t{{.Ports}}'
```

Stop stale run container:

```bash
docker ps -q --filter "name=xarm6_ws-xarm6_sim-run" | xargs -I {} docker stop {}
```

Clean and rebuild ROS artifacts:

```bash
rm -rf ros2/build ros2/install ros2/log
./ros2/build.sh
```

Check noVNC endpoint:

```bash
curl -I http://localhost:6080/vnc.html
```

Known Apple Silicon limitation:

- Gazebo (gz) may crash in this environment.
- Fake mode with RViz is the most reliable path.

---

## Python SDK Section (No Docker)

### Prerequisites

1. Python 3
2. xArm Python SDK installed in your active Python environment
3. Network access to the robot controller

### Installation

```bash
python3 -m pip install xarm-python-sdk
```

### Execution

Run simple sequence script:

```bash
cd /Users/svalliappan/xarm6_ws
python3 python_sdk/simple_xarm_movements.py
```

Run torque-based script:

```bash
cd /Users/svalliappan/xarm6_ws
python3 python_sdk/xarm_torque_movements.py
```

Before running SDK scripts:

- Set the correct robot IP in the script.
- Ensure the workcell is clear.
- Confirm E-stop and safety procedures are ready.

---

## Recommended Daily Flow

1. Validate planning and motion behavior in the ROS 2 section first.
2. Run direct hardware script tests in the Python SDK section.
3. Use only one control path at a time (ROS control or direct SDK).

## ROS 2 Software Versions

| Software | Version |
|---|---|
| ROS 2 | Humble Hawksbill (Ubuntu 22.04) |
| MoveIt 2 | 2.5.x |
| Gazebo | Ignition Fortress |
| Docker base image | ros:humble |
| VNC | TigerVNC |
| noVNC | latest apt |
