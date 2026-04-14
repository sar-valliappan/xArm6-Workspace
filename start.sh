#!/bin/bash
# =============================================================================
# xArm6 Simulation Launcher
# Starts virtual display + VNC + noVNC, then launches MoveIt2 + Gazebo.
# Open: http://localhost:6080/vnc.html?autoconnect=1&resize=remote
# =============================================================================

set -e

# Default to a stable launch mode on ARM64.
# Use XARM_SIM_MODE=gazebo to force full Gazebo simulation.
XARM_SIM_MODE=${XARM_SIM_MODE:-fake}
# Set to true to include the standard xArm gripper in the robot model.
XARM_ADD_GRIPPER=${XARM_ADD_GRIPPER:-false}
# Set to 1 to auto-run pick-and-place demo after startup.
XARM_RUN_DEMO=${XARM_RUN_DEMO:-0}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "=============================================="
echo "  xArm6 ROS 2 Simulation"
echo "  Open: http://localhost:6080/vnc.html?autoconnect=1&resize=remote"
echo "  Password: ros"
echo "=============================================="
echo ""

# Stop stale run containers so ports are free before launching again.
STALE_CONTAINERS=$(docker ps -q --filter "name=xarm6_ws-xarm6_sim-run")
if [ -n "$STALE_CONTAINERS" ]; then
       echo "--> Stopping stale simulation containers..."
       docker stop $STALE_CONTAINERS >/dev/null 2>&1 || true
fi

docker compose run --rm --publish 6080:6080 \
       -e XARM_SIM_MODE="$XARM_SIM_MODE" \
       -e XARM_ADD_GRIPPER="$XARM_ADD_GRIPPER" \
       -e XARM_RUN_DEMO="$XARM_RUN_DEMO" \
    xarm6_sim bash -c '
        set -e
        cd /home/ws

        export DISPLAY=:1
        export LIBGL_ALWAYS_SOFTWARE=1
        export GALLIUM_DRIVER=llvmpipe
        export MESA_GL_VERSION_OVERRIDE=3.3
        export MESA_GLSL_VERSION_OVERRIDE=330
        export OGRE_RTT_MODE=Copy
        export LD_PRELOAD=/usr/lib/aarch64-linux-gnu/libatomic.so.1

        echo "--> Starting virtual display (Xvfb)..."
        Xvfb :1 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset &
        sleep 1

        echo "--> Starting window manager (fluxbox)..."
        fluxbox >/tmp/fluxbox.log 2>&1 &
        sleep 1

        echo "--> Disabling screen lock..."
        DISPLAY=:1 xfconf-query -c xfce4-screensaver -p /lock/enabled -s false 2>/dev/null || true
        DISPLAY=:1 xfconf-query -c xfce4-screensaver -p /screensaver/enabled -s false 2>/dev/null || true

        echo "--> Starting VNC server (x11vnc)..."
        x11vnc -display :1 -forever -shared -nopw \
               -listen 0.0.0.0 -rfbport 5900 \
               >/tmp/x11vnc.log 2>&1 &
        sleep 1

        echo "--> Starting noVNC (websockify)..."
        cd /tmp && websockify --web=/usr/share/novnc/ \
               0.0.0.0:6080 localhost:5900 \
               >/tmp/websockify.log 2>&1 &
        sleep 1

        cd /home/ws
        source /opt/ros/humble/setup.bash
        [ -f /home/ws/install/setup.bash ] && source /home/ws/install/setup.bash

        echo ""
        echo "=============================================="
        echo "  Desktop ready!"
        echo "  Open: http://localhost:6080/vnc.html?autoconnect=1&resize=remote"
        echo "=============================================="
        echo ""

                    if [ "$XARM_SIM_MODE" = "gazebo" ]; then
                           echo "--> Launching xArm6 MoveIt 2 + Gazebo (GZ Sim)..."
                           ros2 launch xarm_moveit_config xarm6_moveit_gazebo.launch.py add_gripper:=$XARM_ADD_GRIPPER gz_type:=gz
                    else
                           echo "--> Launching xArm6 MoveIt 2 (fake mode, stable)..."
                           ros2 launch xarm_moveit_config xarm6_moveit_fake.launch.py add_gripper:=$XARM_ADD_GRIPPER &
                           LAUNCH_PID=$!

                           if [ "$XARM_RUN_DEMO" = "1" ]; then
                                  echo "--> Waiting for controllers, then running pick-place demo..."
                                  sleep 8
                                  ros2 run xarm_pick_place pick_place_node.py || true
                           fi

                           wait $LAUNCH_PID
                    fi
    '
