# Multi-Camera Smoking Detection Documentation

This documentation provides an overview of the codebase and its components.

## Target Detection Labels & Logic
*   **Target Classes**: The system parses the following labels from the YOLO detection model:
    *   `0`: `'rokok'` (Cigarette)
    *   `1`: `'orang'` (Person)
*   **Logged Event**: `'merokok'` (Smoking event) - generated only when a `'rokok'` label is detected within a certain proximity threshold (`Config.PROXIMITY_THRESHOLD`) of an `'orang'` label.
*   **Code Location**: 
    *   Mapping dictionary `class_names = {0: 'rokok', 1: 'orang'}` is defined inside `_process` in `src/camera/camera_instance.py` ([source](./src/camera/camera_instance.py)).
    *   Proximity check and log trigger logic is located inside `_process` in `src/camera/camera_instance.py` ([source](./src/camera/camera_instance.py)).

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

## Additional Files
*   `.env.example`: Example environment configuration.
*   `requirements.txt`: Python package dependencies.
*   `README.md`: General setup and feature information. ([source](./README.md))
