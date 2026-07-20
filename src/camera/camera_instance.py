import os
import cv2
import time
import re
import uuid
import numpy as np
import threading
#import math
import traceback
import queue
from datetime import datetime
from sqlalchemy.exc import OperationalError

from src import db, notification_queue
from src.models import DetectionLog
from src.config import Config

log_queue = queue.Queue()

# Configuration for captured detection images
CAPTURE_MAX_WIDTH = 1280
CAPTURE_QUALITY = 85


def _ensure_captures_dir(app):
    """Ensure the captures directory inside the Flask instance folder exists."""
    captures_dir = os.path.join(app.instance_path, 'captures')
    os.makedirs(captures_dir, exist_ok=True)
    return captures_dir


def _sanitize_cam_name(cam_name):
    """Create a filesystem-safe slug from the camera name."""
    if not cam_name:
        return 'unknown'
    return re.sub(r'[^a-zA-Z0-9_-]', '_', cam_name).lower()[:30]


def _resize_for_storage(image_bytes, max_width=CAPTURE_MAX_WIDTH):
    """Decode JPEG bytes, resize if wider than max_width, re-encode to bytes."""
    try:
        np_arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None:
            return image_bytes

        height, width = img.shape[:2]
        if width > max_width:
            scale = max_width / width
            new_size = (max_width, int(height * scale))
            img = cv2.resize(img, new_size, interpolation=cv2.INTER_AREA)

        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), CAPTURE_QUALITY]
        success, buffer = cv2.imencode('.jpg', img, encode_params)
        return buffer.tobytes() if success else image_bytes
    except Exception as e:
        print(f"Image resize error: {e}")
        return image_bytes


def _save_detection_image(app, image_bytes, cam_name):
    """Persist detection image to disk and return (absolute_path, filename)."""
    try:
        captures_dir = _ensure_captures_dir(app)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_cam = _sanitize_cam_name(cam_name)
        short_id = uuid.uuid4().hex[:8]
        filename = f"detection_{timestamp}_{safe_cam}_{short_id}.jpg"
        file_path = os.path.join(captures_dir, filename)

        processed_bytes = _resize_for_storage(image_bytes)
        with open(file_path, 'wb') as f:
            f.write(processed_bytes)

        return file_path, filename
    except Exception as e:
        print(f"Failed to save detection image: {e}")
        traceback.print_exc()
        return None, None


def detection_log_worker(app):
    """Background thread to write detection logs from the queue to the database."""
    while True:
        try:
            item = log_queue.get()
            if item is None:
                break  # Poison pill to stop the thread

            # Backward compatibility: older queued items may not contain image bytes
            if len(item) >= 4:
                class_name, confidence, cam_name, image_bytes = item
            else:
                class_name, confidence, cam_name = item
                image_bytes = None

            with app.app_context():
                try:
                    image_path = None
                    image_filename = None
                    if image_bytes:
                        image_path, image_filename = _save_detection_image(app, image_bytes, cam_name)

                    detection = DetectionLog(
                        detail=class_name,
                        confidence=confidence,
                        cam=cam_name,
                        image_path=image_path,
                        image_filename=image_filename
                    )
                    db.session.add(detection)
                    db.session.commit()
                    print(f"{cam_name}: Logged {class_name} ({confidence:.2f}) [queue]")
                except OperationalError as e:
                    print(f"{cam_name} database error: {str(e)}")
                    db.session.rollback()
                except Exception as e:
                    print(f"{cam_name} database error: {str(e)}")
                    db.session.rollback()
        except Exception as e:
            print(f"Logging thread error: {e}")
            traceback.print_exc()


class Camera:
    def __init__(self, source, name, width=1280, height=720, fps=30, rtsp_transport='tcp'):
        self.source = source
        self.name = name
        self.width = width
        self.height = height
        self.fps = fps
        self.rtsp_transport = rtsp_transport
        self.latest_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        self.frame_lock = threading.Lock()
        self.running = False
        self.thread = None
        self.last_detection_time = {}
        self.model = None
        self.cap = None
        self.app = None
        self.min_confidence = 0.5
        self.min_interval = 5
        #self.proximity_threshold = 0.2  # 20% of frame width
        
    def get_video_capture(self):
        """Create a new video capture object based on configuration"""
        if self.source.isdigit():
            cap = cv2.VideoCapture(int(self.source))
        elif self.source.startswith('rtsp'):
            os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = f'rtsp_transport;{self.rtsp_transport}'
            cap = cv2.VideoCapture(self.source, cv2.CAP_FFMPEG)
        else:
            cap = cv2.VideoCapture(self.source)
            
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            cap.set(cv2.CAP_PROP_FPS, self.fps)
        return cap
    
    def create_error_frame(self, message):
        """Create a placeholder frame with error message"""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(frame, message, (50, 240), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        cv2.putText(frame, f"Camera: {self.name}", (50, 280), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        return frame
    
    def start(self, model, min_confidence, min_interval):
        if not self.running:
            self.model = model
            self.min_confidence = min_confidence
            self.min_interval = min_interval
            
            print(f"Initializing camera: {self.name} ({self.source})")
            self.cap = self.get_video_capture()
            
            if not self.cap.isOpened():
                print(f"Error opening camera: {self.name}")
                with self.frame_lock:
                    self.latest_frame = self.create_error_frame("Camera Error")
                return False
                
            self.running = True
            self.thread = threading.Thread(target=self._process)
            self.thread.daemon = True
            self.thread.start()
            return True
        return False
    
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
        if self.cap:
            self.cap.release()
    
    def get_latest_frame(self):
        """Get the latest annotated frame with thread safety"""
        with self.frame_lock:
            return self.latest_frame
    
    #def _calculate_distance(self, box1, box2):
        """Calculate normalized distance between centers of two boxes"""
        #x1_center = (box1[0] + box1[2]) / 2
        #y1_center = (box1[1] + box1[3]) / 2
        #x2_center = (box2[0] + box2[2]) / 2
        #y2_center = (box2[1] + box2[3]) / 2
        
        #distance = math.sqrt((x1_center - x2_center)**2 + (y1_center - y2_center)**2)
        #max_possible = math.sqrt(self.width**2 + self.height**2)
        #return distance / max_possible
    
    def _process(self):
        print(f"Starting detection on: {self.name}")
        reconnect_attempts = 0
        max_reconnect_attempts = 5
        
        while self.running:
            if not self.cap.isOpened():
                if reconnect_attempts < max_reconnect_attempts:
                    print(f"{self.name}: Reconnecting...")
                    self.cap = self.get_video_capture()
                    reconnect_attempts += 1
                    time.sleep(2)
                    continue
                else:
                    print(f"{self.name}: Max reconnect attempts reached")
                    with self.frame_lock:
                        self.latest_frame = self.create_error_frame("Camera Disconnected")
                    self.running = False
                    break
            
            success, frame = self.cap.read()
            if not success:
                print(f"{self.name}: Camera read error")
                self.cap.release()
                reconnect_attempts = 0
                time.sleep(1)
                continue
            
            # Let YOLOv10 handle internal letterbox resizing for accurate inference
            # We only resize the frame here for output visualization if needed,
            # but ideally we pass the original frame to model.track.
            reconnect_attempts = 0
            
            try:
                # 1. Gunakan predict (bukan track), serahkan filter confidence ke YOLO
                # with self.model_lock:  # lock dibagikan dari CameraManager
                results = self.model(frame, verbose=False, conf=self.min_confidence, imgsz=416)
                
                smoking_detected = False
                highest_conf = 0.0

                # 2. Cek hasil deteksi
                if results and len(results[0].boxes) > 0:
                    boxes = results[0].boxes
                    classes = boxes.cls.cpu().numpy().astype(int)
                    confidences = boxes.conf.cpu().numpy()
                    
                    for i in range(len(boxes)):
                        class_id = classes[i]
                        conf = confidences[i]
                        class_name = self.model.names.get(class_id, 'unknown')
                        
                        if class_name in ['merokok']:
                            smoking_detected = True
                            if conf > highest_conf:
                                highest_conf = conf

                # 3. Gunakan plotter bawaan YOLO (menjamin posisi bounding box presisi)
                annotated_frame = results[0].plot()
                
                # 4. Resize akhir hanya untuk tampilan antarmuka (web)
                annotated_frame = cv2.resize(annotated_frame, (self.width, self.height))
                
                # Log event if detected
                if smoking_detected:
                    current_time = time.time()
                    last_time = self.last_detection_time.get(self.name, 0)
                    
                    if current_time - last_time > self.min_interval:
                        self.last_detection_time[self.name] = current_time
                        success_encode, buffer = cv2.imencode('.jpg', annotated_frame)
                        image_bytes = buffer.tobytes() if success_encode else None
                        self._log_detection('merokok', highest_conf, image_bytes)
                
                with self.frame_lock:
                    self.latest_frame = annotated_frame
                
            except Exception as e:
                print(f"{self.name} detection error: {str(e)}")
                traceback.print_exc()
            
            time.sleep(1 / self.fps)
        
        if self.cap:
            self.cap.release()
        print(f"Detection stopped for {self.name}")
    
    def _log_detection(self, class_name, confidence, image_bytes=None):
        try:
            log_queue.put((class_name, confidence, self.name, image_bytes))
        except Exception as e:
            print(f"Failed to enqueue detection log: {e}")
        
        if class_name == 'merokok':
            try:
                # Use the imported notification_queue
                notification_queue.put((self.name, confidence))
            except Exception as e:
                print(f"Failed to enqueue notification: {e}")