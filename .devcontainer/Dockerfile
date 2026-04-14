FROM ros:humble

ARG USERNAME=ros
ARG USER_UID=1000
ARG USER_GID=$USER_UID

# Delete user if it exists in container (e.g Ubuntu Noble: ubuntu)
RUN if id -u $USER_UID 2>/dev/null; then userdel `id -un $USER_UID`; fi

# Create the user
RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && apt-get update \
    && apt-get install -y sudo \
    && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME

# ── Base tools ───────────────────────────────────────────────────────────────
RUN apt-get update && apt-get upgrade -y \
    && apt-get install -y \
        python3-pip \
        curl \
        lsb-release \
        gnupg2 \
        python3-colcon-common-extensions \
        python3-rosdep \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get install -y \
    build-essential \
    gcc \
    g++ \
    cmake

# ── Add OSRF Gazebo repo FIRST before any other installs ────────────────────
RUN curl https://packages.osrfoundation.org/gazebo.gpg \
        --output /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] \
       http://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" \
       > /etc/apt/sources.list.d/gazebo-stable.list \
    && apt-get update

# ── VNC + lightweight desktop ────────────────────────────────────────────────
RUN apt-get install -y --fix-missing \
        tigervnc-standalone-server \
        tigervnc-common \
        novnc \
        websockify \
        dbus-x11 \
        x11-utils \
        x11-xserver-utils \
    && rm -rf /var/lib/apt/lists/*

# ── Mesa software rendering (no GPU passthrough on macOS Docker) ─────────────
RUN apt-get update && apt-get install -y --fix-missing \
        libgl1-mesa-dri \
        libgl1-mesa-glx \
        mesa-utils \
        libglu1-mesa \
        libatomic1 \
    && rm -rf /var/lib/apt/lists/*

# ── ROS 2 Humble packages ────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --fix-missing \
        ros-humble-rviz2 \
        ros-humble-moveit \
        ros-humble-moveit-ros-planning-interface \
        ros-humble-moveit-visual-tools \
        ros-humble-moveit-servo \
        ros-humble-xacro \
        ros-humble-robot-state-publisher \
        ros-humble-joint-state-publisher \
        ros-humble-joint-state-publisher-gui \
        ros-humble-ros2-control \
        ros-humble-ros2-controllers \
        ros-humble-controller-manager \
        ros-humble-joint-trajectory-controller \
        ros-humble-joint-state-broadcaster \
        ros-humble-ros-gz-sim \
        ros-humble-ros-gz-bridge \
        ros-humble-ros-gz-interfaces \
        ros-humble-tf2-tools \
        ros-humble-rqt \
        ros-humble-rqt-common-plugins \
    && rm -rf /var/lib/apt/lists/*

# ── Ignition Fortress ────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y ignition-fortress \
    && rm -rf /var/lib/apt/lists/*

# ── rosdep init ──────────────────────────────────────────────────────────────
RUN rosdep init || true

# ── VNC startup script ───────────────────────────────────────────────────────
RUN printf '#!/bin/bash\n\
export DISPLAY=:1\n\
mkdir -p ~/.vnc\n\
echo "ros" | vncpasswd -f > ~/.vnc/passwd\n\
chmod 600 ~/.vnc/passwd\n\
vncserver :1 -geometry 1920x1080 -depth 24 -localhost no &\n\
sleep 2\n\
websockify --web /usr/share/novnc/ 6080 localhost:5901 &\n\
echo "VNC desktop ready at http://localhost:6080 (password: ros)"\n\
wait\n' > /usr/local/bin/start-vnc.sh \
    && chmod +x /usr/local/bin/start-vnc.sh

# ── Environment ──────────────────────────────────────────────────────────────
ENV SHELL=/bin/bash
ENV DISPLAY=:1
ENV LIBGL_ALWAYS_SOFTWARE=1
ENV GALLIUM_DRIVER=llvmpipe
ENV MESA_GL_VERSION_OVERRIDE=3.3
ENV MESA_GLSL_VERSION_OVERRIDE=330
ENV OGRE_RTT_MODE=Copy
ENV LD_PRELOAD=/usr/lib/aarch64-linux-gnu/libatomic.so.1

USER $USERNAME

RUN rosdep update

RUN echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc \
    && echo "[ -f /home/ws/install/setup.bash ] && source /home/ws/install/setup.bash" >> ~/.bashrc

CMD ["/bin/bash"]