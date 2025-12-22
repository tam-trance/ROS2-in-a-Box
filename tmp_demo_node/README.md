# Demo Node Crash Course

This directory (`tmp_demo_node`) serves as a minimal, standalone example of how to create your own ROS 2 package/node within the root of this workspace using `rules_ros2`.

It demonstrates the basic structure for a Python-based ROS 2 application, including library separation, binary creation, and testing.

## Directory Structure

```text
tmp_demo_node/
├── BUILD           # Bazel build definition
├── src/
│   ├── tmp_demo.py         # Main entry point script
│   └── tmp_demo_library.py # Reusable logic/library
└── tests/
    └── tmp_demo_test.py    # Unit tests
```

## How It Works

1.  **Library (`py_library`)**:
    - The core logic is defined in `src/tmp_demo_library.py`.
    - It depends on `@ros2_rclpy//:rclpy`, which is provided by the `rules_ros2` setup.
    - Defined as `tmp_demo_library` in `BUILD`.

2.  **Binary (`py_binary`)**:
    - The executable entry point is `src/tmp_demo.py`.
    - It depends on the local library `//tmp_demo_node:tmp_demo_library`.
    - Defined as `tmp_demo` in `BUILD`.

3.  **Test (`py_test`)**:
    - Tests are located in `tests/`.
    - They verify the functionality of the library.
    - Defined as `tmp_demo_test` in `BUILD`.

## Usage

### 1. Run the Node

To run the demo node:

```bash
bazel run //tmp_demo_node:tmp_demo
```

You should see output like:
```text
[INFO] [launch]: ...
[INFO] [tmp_demo]: Hello, World!
```
(Note: The node spins indefinitely until interrupted).

### 2. Run the Tests

To run the unit tests associated with this node:

```bash
bazel test //tmp_demo_node:tmp_demo_test
```

## Creating Your Own Node

To create a new node in this workspace:

1.  **Create a Directory**: `mkdir my_awesome_node`
2.  **Create Source Files**: Write your ROS 2 code (Python or C++) in `src/`.
3.  **Create `BUILD` File**: Define your targets using `py_binary`, `ros2_cpp_binary`, etc.
    - **Dependencies**: Use `@ros2_rclpy//:rclpy` or `@ros2_rclcpp//:rclcpp` for ROS 2 libraries.
    - **Messages**: If you need standard messages, depend on `@ros2_common_interfaces//:std_msgs` (or `py_std_msgs`/`cpp_std_msgs`).
4.  **Run with Bazel**: Use `bazel run //my_awesome_node:target_name`.

## Tips

- **Imports**: Ensure your `py_binary` or `py_test` targets include `imports = ["src"]` if your python files are inside a subdirectory, or structure your imports relative to the package root.
- **External Dependencies**: You can easily pull in third-party python packages via `pip` dependencies defined in `MODULE.bazel` if needed.
