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

RUN apt-get update && apt-get upgrade -y
RUN apt-get install -y \
    python3-pip \
    curl \
    lsb-release \
    gnupg2 \
    python3-colcon-common-extensions \
    python3-rosdep

# ── Display stack ────────────────────────────────────────────────────────────
RUN apt-get install -y \
    xvfb \
    x11vnc \
    fluxbox \
    novnc \
    websockify \
    dbus-x11 \
    x11-utils \
    x11-xserver-utils \
    xterm

# Remove screen lock so it never activates in the browser desktop
RUN apt-get update && apt-get remove -y xfce4-screensaver 2>/dev/null || true

# Mesa software rendering (no GPU passthrough on macOS Docker)
RUN apt-get install -y \
    libgl1-mesa-dri \
    libgl1-mesa-glx \
    mesa-utils \
    libglu1-mesa \
    libatomic1

# ── ROS 2 Humble packages ────────────────────────────────────────────────────
RUN apt-get install -y \
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
    ros-humble-gz-ros2-control \
    ros-humble-ros-gz-interfaces \
    ros-humble-tf2-tools \
    ros-humble-rqt \
    ros-humble-rqt-common-plugins

# ── Ignition Fortress (ARM64-compatible Gazebo for Humble) ───────────────────
RUN curl https://packages.osrfoundation.org/gazebo.gpg \
        --output /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] \
       http://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" \
       > /etc/apt/sources.list.d/gazebo-stable.list \
    && apt-get update \
    && apt-get install -y ignition-fortress

# rosdep init
RUN rosdep init || true

# Create ROS 2 workspace
RUN mkdir -p /home/ws/src
WORKDIR /home/ws

ENV SHELL=/bin/bash
ENV DISPLAY=:1
ENV LIBGL_ALWAYS_SOFTWARE=1
ENV GALLIUM_DRIVER=llvmpipe
ENV MESA_GL_VERSION_OVERRIDE=3.3
ENV MESA_GLSL_VERSION_OVERRIDE=330
ENV OGRE_RTT_MODE=Copy
ENV LD_PRELOAD=/usr/lib/aarch64-linux-gnu/libatomic.so.1
ENV ROS_DISTRO=humble

USER $USERNAME

RUN rosdep update

RUN echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc \
    && echo "[ -f /home/ws/install/setup.bash ] && source /home/ws/install/setup.bash" >> ~/.bashrc

CMD ["/bin/bash"]
