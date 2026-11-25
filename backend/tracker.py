"""
Object-Specific Movement Detection and Tracking System
Core tracker module using YOLOv8 + ByteTrack
"""

import cv2
import numpy as np
import math
import json
import os
import tempfile
from collections import defaultdict
from ultralytics import YOLO

# imageio-ffmpeg bundles its own ffmpeg → produces browser-playable H.264
try:
    import imageio
    import imageio.v3 as iio
    _IMAGEIO_OK = True
except ImportError:
    _IMAGEIO_OK = False


# ─────────────────────────── YOLO class labels ───────────────────────────────
COCO_CLASSES = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train",
    "truck", "boat", "traffic light", "fire hydrant", "stop sign",
    "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep",
    "cow", "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella",
    "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard",
    "sports ball", "kite", "baseball bat", "baseball glove", "skateboard",
    "surfboard", "tennis racket", "bottle", "wine glass", "cup", "fork",
    "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange",
    "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair",
    "couch", "potted plant", "bed", "dining table", "toilet", "tv",
    "laptop", "mouse", "remote", "keyboard", "cell phone", "microwave",
    "oven", "toaster", "sink", "refrigerator", "book", "clock", "vase",
    "scissors", "teddy bear", "hair drier", "toothbrush",
]

# Colour palette — one vivid colour per track ID
PALETTE = [
    (255, 56, 56), (255, 157, 151), (255, 112, 31), (255, 178, 29),
    (207, 210, 49), (72, 249, 10), (146, 204, 23), (61, 219, 134),
    (26, 147, 52), (0, 212, 187), (44, 153, 168), (0, 194, 255),
    (52, 69, 147), (100, 115, 255), (0, 24, 236), (132, 56, 255),
    (82, 0, 133), (203, 56, 255), (255, 149, 200), (255, 55, 199),
]


def get_color(track_id: int):
    return PALETTE[track_id % len(PALETTE)]


def compute_direction(dx: float, dy: float) -> str:
    """Return compass direction for a displacement vector."""
    if abs(dx) < 1 and abs(dy) < 1:
        return "Stationary"
    angle = math.degrees(math.atan2(-dy, dx))  # screen y is inverted
    angle = (angle + 360) % 360
    dirs = ["East", "NE", "North", "NW", "West", "SW", "South", "SE"]
    idx = round(angle / 45) % 8
    return dirs[idx]


# ─────────────────────────── Main Tracker class ───────────────────────────────
class ObjectTracker:
    def __init__(self, model_path: str = "yolov8n.pt", conf: float = 0.35):
        self.model = YOLO(model_path)
        self.conf = conf

        # Per-track history
        self.trajectories: dict[int, list[tuple[int, int]]] = defaultdict(list)
        self.frame_data: list[dict] = []          # one entry per frame

    # ── helpers ──────────────────────────────────────────────────────────────
    def _centre(self, box) -> tuple[int, int]:
        x1, y1, x2, y2 = box
        return int((x1 + x2) / 2), int((y1 + y2) / 2)

    # ── first pass: detect + track every frame ────────────────────────────────
    def process_video(self, video_path: str) -> dict:
        """
        Run YOLOv8 + ByteTrack on the full video.
        Returns a summary dict with per-frame detections and unique objects.
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")

        fps        = cap.get(cv2.CAP_PROP_FPS) or 30
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        w          = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h          = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        self.trajectories.clear()
        self.frame_data.clear()

        all_objects: dict[int, dict] = {}  # track_id → {class, frames}

        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            results = self.model.track(
                frame,
                persist=True,
                conf=self.conf,
                tracker="bytetrack.yaml",
                verbose=False,
            )

            frame_detections = []
            if results and results[0].boxes is not None:
                boxes = results[0].boxes
                for i, box in enumerate(boxes):
                    if box.id is None:
                        continue
                    tid  = int(box.id.item())
                    cls  = int(box.cls.item())
                    conf = float(box.conf.item())
                    x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                    cx, cy = self._centre((x1, y1, x2, y2))

                    self.trajectories[tid].append((cx, cy))
                    label = COCO_CLASSES[cls] if cls < len(COCO_CLASSES) else "unknown"

                    frame_detections.append({
                        "track_id": tid,
                        "class": label,
                        "conf": round(conf, 3),
                        "bbox": [x1, y1, x2, y2],
                        "centre": [cx, cy],
                        "frame": frame_idx,
                    })

                    if tid not in all_objects:
                        all_objects[tid] = {
                            "track_id": tid,
                            "class": label,
                            "first_frame": frame_idx,
                            "last_frame": frame_idx,
                            "conf": round(conf, 3),
                        }
                    else:
                        all_objects[tid]["last_frame"] = frame_idx

            self.frame_data.append({"frame": frame_idx, "detections": frame_detections})
            frame_idx += 1

        cap.release()

        return {
            "total_frames": frame_idx,
            "fps": fps,
            "width": w,
            "height": h,
            "total_frames_actual": total_frames,
            "objects": list(all_objects.values()),
        }

    # ── second pass: render annotated video for ONE selected object ───────────
    def render_tracked_video(
        self,
        video_path: str,
        selected_id: int,
        output_path: str,
    ) -> dict:
        """
        Re-read the video and annotate only the selected track ID.
        Returns movement analysis metrics.
        """
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        w   = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h   = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()

        color = get_color(selected_id)
        trajectory_pts: list[tuple[int, int]] = []
        speeds:  list[float] = []
        displacements_x: list[float] = []
        displacements_y: list[float] = []
        directions: list[str] = []
        prev_centre: tuple[int, int] | None = None
        label_cls = "object"

        # ── Collect annotated frames in memory ────────────────────────────────
        annotated_frames: list[np.ndarray] = []

        cap = cv2.VideoCapture(video_path)
        for finfo in self.frame_data:
            ret, frame = cap.read()
            if not ret:
                break

            # draw ALL detections lightly (grey)
            for det in finfo["detections"]:
                if det["track_id"] == selected_id:
                    continue
                x1, y1, x2, y2 = det["bbox"]
                cv2.rectangle(frame, (x1, y1), (x2, y2), (80, 80, 80), 1)

            # highlight selected object
            sel_det = next(
                (d for d in finfo["detections"] if d["track_id"] == selected_id), None
            )
            if sel_det:
                label_cls = sel_det["class"]
                x1, y1, x2, y2 = sel_det["bbox"]
                cx, cy = sel_det["centre"]
                trajectory_pts.append((cx, cy))

                # displacement & speed
                if prev_centre:
                    dx = cx - prev_centre[0]
                    dy = cy - prev_centre[1]
                    dist = math.hypot(dx, dy)
                    speed_pps = dist * fps          # pixels per second
                    displacements_x.append(float(dx))
                    displacements_y.append(float(dy))
                    speeds.append(float(speed_pps))
                    directions.append(compute_direction(dx, dy))

                    # draw motion arrow
                    if dist > 2:
                        cv2.arrowedLine(
                            frame,
                            prev_centre, (cx, cy),
                            (0, 255, 255), 2, tipLength=0.4,
                        )

                prev_centre = (cx, cy)

                # bounding box
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                # label
                tag = f"ID:{selected_id} {label_cls}"
                (tw, th), _ = cv2.getTextSize(tag, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                cv2.rectangle(frame, (x1, y1 - th - 8), (x1 + tw + 4, y1), color, -1)
                cv2.putText(frame, tag, (x1 + 2, y1 - 4),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

                # draw trajectory trail
                for k in range(1, len(trajectory_pts)):
                    alpha = k / len(trajectory_pts)
                    tc = tuple(int(c * alpha) for c in color)
                    cv2.line(frame, trajectory_pts[k - 1], trajectory_pts[k], tc, 2)

                # draw centre dot
                cv2.circle(frame, (cx, cy), 5, color, -1)

            # frame counter
            cv2.putText(
                frame,
                f"Frame {finfo['frame']}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2,
            )

            annotated_frames.append(frame)

        cap.release()

        # ── Write output video ────────────────────────────────────────────────
        # Try imageio-ffmpeg first (bundles its own ffmpeg → true H.264)
        written = False
        if _IMAGEIO_OK and annotated_frames:
            try:
                writer = imageio.get_writer(
                    output_path,
                    fps=fps,
                    codec="libx264",
                    quality=None,
                    output_params=[
                        "-crf", "23",
                        "-preset", "fast",
                        "-movflags", "+faststart",
                        "-pix_fmt", "yuv420p",
                    ],
                )
                for frame in annotated_frames:
                    writer.append_data(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                writer.close()
                written = True
            except Exception as e:
                print(f"[imageio] H.264 write failed ({e}), falling back to OpenCV")

        # Fallback: OpenCV VideoWriter with mp4v
        if not written:
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            out    = cv2.VideoWriter(output_path, fourcc, fps, (w, h))
            for frame in annotated_frames:
                out.write(frame)
            out.release()

        # ── compute analytics ──
        avg_speed  = float(np.mean(speeds)) if speeds else 0.0
        max_speed  = float(np.max(speeds))  if speeds else 0.0
        total_dist = float(sum(math.hypot(dx, dy)
                               for dx, dy in zip(displacements_x, displacements_y)))

        most_common_dir = (
            max(set(directions), key=directions.count) if directions else "N/A"
        )

        # net displacement from first to last centre
        if len(trajectory_pts) >= 2:
            net_dx = trajectory_pts[-1][0] - trajectory_pts[0][0]
            net_dy = trajectory_pts[-1][1] - trajectory_pts[0][1]
        else:
            net_dx, net_dy = 0, 0

        return {
            "track_id": selected_id,
            "class": label_cls,
            "trajectory": [[p[0], p[1]] for p in trajectory_pts],
            "speeds": [round(s, 2) for s in speeds],
            "displacements_x": [round(d, 2) for d in displacements_x],
            "displacements_y": [round(d, 2) for d in displacements_y],
            "directions": directions,
            "avg_speed_px_s": round(avg_speed, 2),
            "max_speed_px_s": round(max_speed, 2),
            "total_distance_px": round(total_dist, 2),
            "primary_direction": most_common_dir,
            "net_displacement": [net_dx, net_dy],
            "frames_tracked": len(trajectory_pts),
        }
