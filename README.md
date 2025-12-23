# ROS2 in a Box

Skip the cumbersome 'build from source' ROS2 installation for MacOS. This repository has what you need to start coding with ROS2 on your MacOS right away. And other OS systems. And beautifully packaged into a Bazel environment, so that it is reproducible anywhere you code. More details below!

This repository represents a robust, self-contained Bazel workspace for developing ROS 2 applications. It features a heavily adapted and "frozen" version of ROS 2 build rules, designed to provide a hermetic and reproducible development environment without requiring a system-level ROS 2 installation.

## Project Philosophy & Architecture

The core idea of this workspace is **"ROS 2 in a Box"**.

We started with the excellent [mvukov/rules_ros2](https://github.com/mvukov/rules_ros2) repository, which provides Bazel rules for ROS 2 Humble. We then significantly transformed it to serve as a stable, foundational **Bazel Module**:

1.  **Modularization**: We converted the original repository into a dedicated submodule (`rules_ros2/`) that acts as a dependency for this root workspace. Your application code lives "outside" the ROS 2 rules, treating the ROS 2 build system as a toolchain rather than a parent project.
    
2.  **Vendoring & Freezing**: We have vendored in all external dependencies (found in `vendor/` and within `rules_ros2`). This "freezes" the dependency tree, ensuring that builds are:
    - **Hermetic**: Independent of the host system's library versions.
    - **Reproducible**: Everyone builds against the exact same code.
    - **Stable**: Immune to upstream changes or breaking updates until we explicitly choose to upgrade.

3.  **Modern Bazel (Bzlmod)**: This project is built for **Bazel 8+** and fully embraces the modern `MODULE.bazel` system (Bzlmod), deprecating the legacy `WORKSPACE` file.

## Directory Structure

```text
ROS2-in-a-Box/
├── MODULE.bazel        # Root module definition
├── rules_ros2/         # The "Frozen" ROS 2 build system (modified & vendored)
│   ├── examples/       # Standard ROS 2 examples (chatter, actions, etc.)
│   └── ...
├── tmp_demo_node/      # Example user code / "Crash Course" on writing nodes
├── vendor/             # Vendored third-party dependencies (curl, etc.)
└── README.md           # This file
```

## Prerequisites

- **Bazel**: Version 8.0 or higher.
- **Python**: Python 3.10+.
- **C++ Compiler**: Clang (recommended) or GCC.
- **OS**: Linux (Ubuntu 22.04, not tested yet) or macOS (Apple Silicon supported, tested on Sonoma 14.5).

**Note:** You do **NOT** need to install ROS 2 (Humble, Iron, etc.) on your host machine as per the instructions from [the Bazel website](https://docs.ros.org/en/humble/Installation.html). This git repository provides everything needed to start building with ROS2.

## Getting Started

### 1. Clone the repo and the submodel

```bash
git clone git@github.com:tam-trance/ROS2-in-a-Box.git
cd ROS2-in-a-Box
git submodule update --init --recursive # this pulls rules_ros2 submodule from https://github.com/tam-trance/rules_ros2.git
```

### 1. Run sanity checks (optional, will take some minutes)

Run each command one at a time. You should still be in `ROS2-in-a-Box` folder.

```bash
bazel build //…
bazel test //…
bazel build @rules_ros2//…
bazel test @rules_ros2//…
bazel run @rules_ros2//examples/chatter:chatter
bazel run @rules_ros2//examples/zero_copy --@cyclonedds//:enable_shm=True
bazel test @rules_ros2//examples/chatter:tests
bazel test @rules_ros2//examples/zero_copy:tests --@cyclonedds//:enable_shm=True --test_output=all
```

Sanity checks for modules as standalone. Now run these from `ROS2-in-a-Box/rules_ros2/examples/` folder.
```bash
cd rules_ros2/examples/
bazel run //actions --experimental_isolated_extension_usages && rm bazel-*
bazel run //chatter --experimental_isolated_extension_usages && rm bazel-*
bazel run //lifecycle --experimental_isolated_extension_usages && rm bazel-*
bazel run //foxglove_bridge --experimental_isolated_extension_usages && rm bazel-*
bazel run //zero_copy --@cyclonedds//:enable_shm=True --experimental_isolated_extension_usages && rm bazel-*
```

All of these should pass without error. Otherwise see `Troubleshooting` below. Warnings are normal. 

**Note:** Running this command likely break and that's fine. `rules_ros2` is meant to run as a submodule, not as its own module.
```bash
cd rules_ros2/
bazel build //...
```

### 2. Run the Demo Node

A sample user-space node is provided in `tmp_demo_node/` to demonstrate how to write code in this workspace.

```bash
bazel run //tmp_demo_node:tmp_demo
```

See [`tmp_demo_node/README.md`](tmp_demo_node/README.md) for a crash course on creating your own nodes.

### 3. Run ROS 2 Examples

The `rules_ros2` module includes standard ROS 2 examples to verify the build system.

**Chatter (Pub/Sub):**
```bash
bazel run @rules_ros2//examples/chatter:chatter
```

**Foxglove Bridge (Visualization):**
```bash
bazel run @rules_ros2//examples/foxglove_bridge:foxglove_bridge
```

See [`rules_ros2/README.md`](rules_ros2/README.md) for detailed documentation on the available tools and configuration.

## Developing Your Own Nodes

To add a new ROS 2 node to this workspace:

1.  Create a new directory (e.g., `my_robot`, at the same level as `tmp_demo_node`).
2.  Add your source code (Python/C++/Rust).
3.  Create a `BUILD` file.
4.  Depend on the targets exposed by `rules_ros2` (e.g., `@ros2_rclpy//:rclpy`, `@ros2_rclcpp//:rclcpp`).
5.  Add the new package to the root build graph (Bazel handles this automatically via path presence).

## Troubleshooting

- **Delete symlinks before building**: If you are getting build issues, delete the symlinks `bazel-*` with `rm -rf bazel-*`.
- **"No module named..."**: Ensure your `py_binary` targets have the correct `imports` or dependencies.
- **Path Issues**: Launch files should use robust path resolution (relative to `__file__`) as demonstrated in the examples, especially because `rules_ros2` is an external dependency.