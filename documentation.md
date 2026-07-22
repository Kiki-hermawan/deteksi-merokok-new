# Multi-Camera Smoking Detection Documentation

This documentation provides an overview of the codebase and its components.

## Target Detection Labels & Logic

* **Target Classes**: The system parses the following label from the YOLO detection model:
    * `0`: `'merokok'` (Smoking)

* **Logged Event**: `'merokok'` (Smoking event) – generated whenever the YOLO model detects the `merokok` class.

* **Detection Logic**:
    * The system directly detects the `merokok` class from the YOLO model.
    * No person detection is required.
    * No proximity calculation is performed.
    * Each valid `merokok` detection is logged according to the configured logging interval.

* **Code Location**:
    * Mapping dictionary `class_names = {0: 'merokok'}` is defined inside `_process` in `src/camera/camera_instance.py` ([source](./src/camera/camera_instance.py)).
    * Detection logging is handled directly inside `_process` in `src/camera/camera_instance.py` ([source](./src/camera/camera_instance.py)).

## Core Application

*   `run.py`: Entry point for running the Flask application. ([source](./run.py))
*   `src/__init__.py`: Application factory (`create_app`), extension initialization (SQLAlchemy, LoginManager), and background task setup. ([source](./src/__init__.py))
*   `src/config.py`: Configuration class loading environment variables from `.env`. ([source](./src/config.py))
*   `src/models.py`: Database models `DetectionLog` and `User`. ([source](./src/models.py))

## Blueprints

### Main (`src/main/`)
*   `src/main/__init__.py`: Blueprint initialization. ([source](./src/main/__init__.py))
*   `src/main/routes.py`: Core application routes (index, video feed streaming, detection log view). ([source](./src/main/routes.py))

### Authentication (`src/auth/`)
*   `src/auth/__init__.py`: Blueprint initialization. ([source](./src/auth/__init__.py))
*   `src/auth/routes.py`: Web-based user authentication routes (login, register, logout, profile). ([source](./src/auth/routes.py))

### API Authentication (`src/api/`)
*   `src/api/__init__.py`: Blueprint initialization. ([source](./src/api/__init__.py))
*   `src/api/routes.py`: JWT-based API authentication routes (`/api/login`, `/api/protected`). ([source](./src/api/routes.py))

## Camera & Detection Engine (`src/camera/`)
*   `src/camera/__init__.py`: Module initialization. ([source](./src/camera/__init__.py))
*   `src/camera/camera_manager.py`: `CameraManager` class to handle multiple `Camera` instances and global YOLO model loading. ([source](./src/camera/camera_manager.py))
*   `src/camera/camera_instance.py`: `Camera` class for video capture, YOLO inference, proximity detection (cigarette near person), and queueing logs/notifications. Also contains `detection_log_worker` thread function. ([source](./src/camera/camera_instance.py))

## Templates (`src/templates/`)
*   `src/templates/index.html`: Main dashboard displaying multiple camera feeds. ([source](./src/templates/index.html))
*   `src/templates/log.html`: Detection log table view (used in iframe). ([source](./src/templates/log.html))
*   `src/templates/login.html`: User login page. ([source](./src/templates/login.html))
*   `src/templates/register.html`: User registration page. ([source](./src/templates/register.html))
*   `src/templates/profile.html`: User profile view. ([source](./src/templates/profile.html))

## Audio Alarm & Dashboard Statistics

### Audio Alarm

*   **Asset**: `alarm.mp3` is served from `src/static/audio/alarm.mp3` (copied from the project root). ([source](./src/static/audio/alarm.mp3))
*   **Frontend trigger**: `src/static/js/dashboard.js` plays the alarm when the live log polling detects a new detection row, with a 10-second cooldown to avoid spamming.
*   **Mute control**: `src/templates/index.html` includes a mute/unmute button in the topbar. The mute state is persisted in `localStorage`.
*   **Browser autoplay note**: Most browsers block audio until the user interacts with the page. The dashboard attempts to unlock the audio context on the first click/touch/key press.

### Dashboard Statistics Charts

*   **Library**: [Chart.js](https://www.chartjs.org/) loaded via CDN in `src/templates/index.html`.
*   **Endpoint**: `src/main/routes.py` exposes `/api/stats` (JSON) that returns:
    *   `detection_status`: `{detected, not_detected}`
    *   `camera_breakdown`: list of `{name, count, percentage}`
    *   `avg_confidence`: average confidence across all logs
*   **Frontend**: `src/static/js/dashboard.js` renders:
    *   A doughnut chart for detected vs. not-detected status.
    *   A bar chart showing the number of detected events per camera.
    *   An additional KPI card for average confidence.
*   **Data note**: The application currently only logs positive `merokok` events, so `not_detected` is always `0`. The charts visualize the proportion of events per camera and the overall detected count.

### Static Assets
*   `src/static/audio/alarm.mp3`: Alarm sound file served by Flask.
*   `src/static/css/style.css`: Added styles for the alarm mute button and chart panel.
*   `src/static/js/dashboard.js`: Updated to handle camera feeds, live log, alarm, and charts.

### Database Changes
*   **No new tables or columns were added** for this feature. The statistics endpoint reads from the existing `detection_logs` table (`DetectionLog` model).

## Additional Files
*   `.env.example`: Example environment configuration.
*   `requirements.txt`: Python package dependencies.
*   `README.md`: General setup and feature information. ([source](./README.md))

.
