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
        self.app = app

    def setup_cameras_from_db(self):
        """Ganti dari setup_cameras_from_config() — kamera kini didaftarkan lewat DB."""
        from src.models import Camera as CameraRecord
        records = CameraRecord.query.filter_by(is_active=True).order_by(CameraRecord.id).all()
        for record in records:
            camera = Camera(
                source=record.build_source(),
                name=record.name,
                width=record.width,
                height=record.height,
                fps=record.fps,
                rtsp_transport=record.rtsp_transport,
                db_id=record.id,
            )
            self.add_camera(camera)

    def add_camera(self, camera):
        camera.app = self.app
        self.cameras.append(camera)

    def _ensure_model_loaded(self):
        """Load model YOLO sekali saja, kapan pun dibutuhkan (bukan cuma saat start())."""
        if self.model is None:
            print(f"Loading model: {Config.MODEL_PATH}")
            self.model = YOLO(Config.MODEL_PATH)
            print("Model loaded successfully")
        return self.model

    def add_camera_runtime(self, record):
        """Tambah kamera baru dari halaman Manajemen Kamera lalu langsung jalankan."""
        camera = Camera(
            source=record.build_source(), name=record.name,
            width=record.width, height=record.height, fps=record.fps,
            rtsp_transport=record.rtsp_transport, db_id=record.id,
        )
        self.add_camera(camera)

        self._ensure_model_loaded()  # <-- load model kalau belum ada, jangan cuma skip

        camera.start(self.model, Config.MIN_CONFIDENCE, Config.MIN_LOG_INTERVAL)

        # pastikan monitor thread juga jalan kalau ini kamera pertama
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._monitor)
            self.thread.daemon = True
            self.thread.start()

        return camera

    def remove_camera(self, db_id):
        camera = self.get_camera(db_id)
        if camera is None:
            return False
        camera.manually_stopped = True
        camera.stop()
        self.cameras.remove(camera)
        return True

    def get_camera(self, camera_id):
        """camera_id sekarang adalah Camera.id di database, bukan posisi list."""
        for cam in self.cameras:
            if cam.db_id == camera_id:
                return cam
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
        while self.running:
            time.sleep(5)
            for camera in self.cameras:
                self._restart_camera_if_needed(camera)

    def _restart_camera_if_needed(self, camera):
        if getattr(camera, "manually_stopped", False):
            return
        thread_dead = camera.thread is None or not camera.thread.is_alive()
        if not camera.running and thread_dead:
            print(f"[INFO] Restarting camera: {camera.name}")
            camera.start(self.model, Config.MIN_CONFIDENCE, Config.MIN_LOG_INTERVAL)

    def stop_camera(self, camera_id):
        camera = self.get_camera(camera_id)
        if camera is None or not camera.running:
            return False
        camera.manually_stopped = True
        camera.stop()
        return True

    def start_camera(self, camera_id):
        camera = self.get_camera(camera_id)
        if camera is None:
            return False
        self._ensure_model_loaded()
        if camera.running:
            return True
        camera.manually_stopped = False
        camera.start(self.model, Config.MIN_CONFIDENCE, Config.MIN_LOG_INTERVAL)
        return camera.running

    def toggle_camera(self, camera_id):
        camera = self.get_camera(camera_id)
        if camera is None:
            return None
        if camera.running:
            self.stop_camera(camera_id)
            return False
        self.start_camera(camera_id)
        return True


processor = CameraManager()