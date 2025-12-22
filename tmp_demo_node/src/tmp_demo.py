

from tmp_demo_library import *

def main(args=None):
    rclpy.init(args=args)
    node = TmpDemo()
    rclpy.spin(node) # spins forever. node is listening for stuff.
    print('Done spinning')
    node.destroy_node()
    rclpy.shutdown()

if __name__ == "__main__":
    main()
    time.sleep(5)
    exit(0)
