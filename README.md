# Perimeta_v2 Workspace

This repository represents a robust, self-contained Bazel workspace for developing ROS 2 applications. It features a heavily adapted and "frozen" version of ROS 2 build rules, designed to provide a hermetic and reproducible development environment without requiring a system-level ROS 2 installation.

## Project Philosophy & Architecture

The core idea of this workspace is **"ROS 2 in a Box"**.

We started with the excellent [mvukov/rules_ros2](https://github.com/mvukov/rules_ros2) repository, which provides Bazel rules for ROS 2. We then significantly transformed it to serve as a stable, foundational **Bazel Module** for our specific needs:

1.  **Modularization**: We converted the original repository into a dedicated submodule (`rules_ros2/`) that acts as a dependency for this root workspace. Your application code lives "outside" the ROS 2 rules, treating the ROS 2 build system as a toolchain rather than a parent project.
    
2.  **Vendoring & Freezing**: We have vendored in all external dependencies (found in `vendor/` and within `rules_ros2`). This "freezes" the dependency tree, ensuring that builds are:
    - **Hermetic**: Independent of the host system's library versions.
    - **Reproducible**: Everyone builds against the exact same code.
    - **Stable**: Immune to upstream changes or breaking updates until we explicitly choose to upgrade.

3.  **Modern Bazel (Bzlmod)**: This project is built for **Bazel 8+** and fully embraces the modern `MODULE.bazel` system (Bzlmod), deprecating the legacy `WORKSPACE` file.

## Directory Structure

```text
Perimeta_v2/
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
- **OS**: Linux (Ubuntu 22.04) or macOS (Apple Silicon supported).

**Note:** You do **NOT** need to install ROS 2 (Humble, Iron, etc.) on your host machine. This workspace provides everything needed.

## Getting Started

### 1. Run the Demo Node

A sample user-space node is provided in `tmp_demo_node/` to demonstrate how to write code in this workspace.

```bash
bazel run //tmp_demo_node:tmp_demo
```

See [`tmp_demo_node/README.md`](tmp_demo_node/README.md) for a crash course on creating your own nodes.

### 2. Run ROS 2 Examples

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

1.  Create a new directory (e.g., `my_robot`).
2.  Add your source code (Python/C++/Rust).
3.  Create a `BUILD` file.
4.  Depend on the targets exposed by `rules_ros2` (e.g., `@ros2_rclpy//:rclpy`, `@ros2_rclcpp//:rclcpp`).
5.  Add the new package to the root build graph (Bazel handles this automatically via path presence).

## Troubleshooting

- **"No module named..."**: Ensure your `py_binary` targets have the correct `imports` or dependencies.
- **Path Issues**: Launch files should use robust path resolution (relative to `__file__`) as demonstrated in the examples, especially because `rules_ros2` is an external dependency.
