import threading
import time
from ultralytics import YOLO
from src.camera.camera_instance import Camera
from src.config import Config

class CameraManager:
    def __init__(self):
        self.cameras = []
        self.model = None
        self.running = False
        self.thread = None
        self.app = None
    
    def set_app(self, app):
        """Binds the Flask app instance to the manager."""
        self.app = app

    def setup_cameras_from_config(self):
        """Sets up cameras based on the global config."""
        for i, source in enumerate(Config.CAMERA_SOURCES):
            name = Config.CAMERA_NAMES[i] if i < len(Config.CAMERA_NAMES) else f"Camera {i+1}"
            width = Config.CAMERA_WIDTHS[i] if i < len(Config.CAMERA_WIDTHS) else 1280
            height = Config.CAMERA_HEIGHTS[i] if i < len(Config.CAMERA_HEIGHTS) else 720
            fps = Config.CAMERA_FPS[i] if i < len(Config.CAMERA_FPS) else 15
            camera = Camera(source=source, name=name, width=width, height=height, fps=fps)
            self.add_camera(camera)
            
    def add_camera(self, camera):
        """Adds a camera and attaches the app context to it."""
        camera.app = self.app
        self.cameras.append(camera)

    def get_camera(self, camera_id):
        if 0 <= camera_id < len(self.cameras):
            return self.cameras[camera_id]
        return None

    def start(self):
        if not self.running and self.cameras:
            print(f"Loading model: {Config.MODEL_PATH}")
            self.model = YOLO(Config.MODEL_PATH)
            print("Model loaded successfully")
            
            self.running = True
            for camera in self.cameras:
                camera.start(self.model, Config.MIN_CONFIDENCE, Config.MIN_LOG_INTERVAL)
            
            self.thread = threading.Thread(target=self._monitor)
            self.thread.daemon = True
            self.thread.start()
    
    def stop(self):
        self.running = False
        for camera in self.cameras:
            camera.stop()
        if self.thread:
            self.thread.join()
    
    def _monitor(self):
        """Monitor camera threads and restart if needed"""
        while self.running:
            time.sleep(5)
            for i, camera in enumerate(self.cameras):
                if not camera.running and camera.thread and not camera.thread.is_alive():
                    print(f"Restarting camera: {camera.name}")
                    camera.start(self.model, self.min_confidence, self.min_interval)

processor = CameraManager()
# inference_lock = threading.Lock()