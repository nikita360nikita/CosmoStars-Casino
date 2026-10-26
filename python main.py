# Auto-forwarder for hosting panels that pass 'python main.py' as the script filename
import runpy

if __name__ == "__main__":
    runpy.run_path("main.py", run_name="__main__")
