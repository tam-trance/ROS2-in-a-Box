

import rclpy
from rclpy.node import Node

import time


class TmpDemo(Node):
    def __init__(self):
        super().__init__("tmp_demo")
        self.get_logger().info("Hello, World!")
