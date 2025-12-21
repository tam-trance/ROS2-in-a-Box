load("@rules_python//python:defs.bzl", "py_binary", "py_library", "py_test")

py_binary(
    name = "tmp_demo",
    srcs = ["src/tmp_demo.py"],
    imports = ["src"],
    visibility = ["//visibility:public"],
    deps = [
        "//tmp_demo_node:tmp_demo_library"
    ]
)

py_library(
    name = "tmp_demo_library",
    srcs = ["src/tmp_demo_library.py"],
    deps = [
        "@ros2_rclpy//:rclpy"
    ]
)

py_test(
    name = "tmp_demo_test",
    srcs = ["tests/tmp_demo_test.py"],
    imports = ["src"],
    deps = [
        "//tmp_demo_node:tmp_demo_library"
    ]
)