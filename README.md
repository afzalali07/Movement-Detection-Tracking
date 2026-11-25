# VisionTrack 🎯
## Object-Specific Movement Detection & Tracking Using Video Datasets

> A Python + web-based system that detects multiple objects in a video using **YOLOv8**, assigns unique IDs with **ByteTrack**, lets the user select a specific object, and estimates its movement, direction, speed, and trajectory — all visualised in a modern dark-themed website.

---

## 📸 Features

| Feature | Details |
|---|---|
| **Object Detection** | YOLOv8 (80 COCO classes — person, car, drone, etc.) |
| **Object Tracking** | ByteTrack persistent IDs across frames |
| **Object Selection** | Interactive web UI card picker |
| **Movement Metrics** | ΔX, ΔY displacement, speed (px/s), total distance |
| **Direction** | 8-way compass estimation per frame |
| **Trajectory** | Full pixel path with gradient trail |
| **Annotated Video** | Bounding boxes, ID labels, motion arrows, trajectory overlay |
| **Graphs** | Trajectory, Speed, Displacement, Direction histogram, Dashboard |
| **Frontend** | Single-page dark-mode website (no React, pure HTML/CSS/JS) |
| **Backend** | Flask REST API |

---

## 🗂️ Project Structure

```
movement-tracking/
├── backend/
│   ├── app.py          # Flask REST API
│   ├── tracker.py      # YOLOv8 + ByteTrack core engine
│   ├── graphs_gen.py   # Matplotlib graph generation
│   ├── uploads/        # Uploaded videos (auto-created)
│   ├── outputs/        # Annotated output videos
│   └── graphs/         # Generated PNG graphs
├── frontend/
│   ├── templates/
│   │   └── index.html  # Main web page
│   └── static/
│       ├── css/style.css
│       └── js/app.js
├── requirements.txt
├── start.bat           # Windows launcher
├── start.sh            # Linux/macOS launcher
└── README.md
```

---

## ⚡ Quick Start

### Windows
```bat
start.bat
```

### Linux / macOS
```bash
chmod +x start.sh
./start.sh
```

Then open **http://localhost:5000** in your browser.

---

## 🔧 Manual Setup

```bash
# 1. Create & activate virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # Linux/macOS

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the Flask server
cd backend
python app.py
```

> YOLOv8 (`yolov8n.pt`) is downloaded automatically on first run (~6 MB).

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/upload` | Upload a video file |
| `POST` | `/api/analyse` | Run YOLOv8 + ByteTrack, return object list |
| `POST` | `/api/track` | Render annotated video + generate graphs for a selected ID |
| `GET`  | `/api/video/<sid>/<tid>` | Stream annotated output video |
| `GET`  | `/api/graphs/<sid>/<file>` | Serve a graph image |
| `GET`  | `/api/health` | Server health check |

---

## 📊 Output Graphs

1. **Trajectory** — Spatial path of the object (gradient coloured)
2. **Speed** — Pixel speed per second over frame index
3. **Displacement** — ΔX and ΔY bar chart per frame
4. **Direction Histogram** — Compass direction distribution
5. **Dashboard** — 4-panel combined summary

---

## 📦 Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `flask` | 2.3.3 | Web framework |
| `flask-cors` | 4.0.0 | Cross-origin requests |
| `ultralytics` | 8.0.196 | YOLOv8 + ByteTrack |
| `opencv-python` | 4.8.1.78 | Frame extraction & rendering |
| `numpy` | 1.26.0 | Numerical operations |
| `matplotlib` | 3.8.0 | Graph generation |
| `Pillow` | 10.1.0 | Image utilities |
| `scipy` | 1.11.3 | Signal processing |

---

## 🎮 Usage Walkthrough

1. **Upload** — Drag & drop or browse for a video (MP4/AVI/MOV/MKV/WebM)
2. **Adjust** — Set detection confidence (0.1 – 0.9)
3. **Analyse** — Click "Upload & Analyse" — YOLOv8+ByteTrack processes all frames
4. **Select** — Click the object card (by ID and class) you want to track
5. **Track** — Click "Track Selected Object" — renders annotated video + graphs
6. **Explore** — Switch tabs: Annotated Video / Trajectory / Speed / Displacement / Direction / Dashboard

---

## 📌 Supported Video Datasets

- **MOT17 / MOT20** — Multi-object tracking benchmarks
- **VIRAT** — Drone & surveillance footage
- **UA-DETRAC** — Vehicle tracking
- **Any custom MP4/AVI** — Works with any real-world video

---

## 📐 Movement Metrics Explained

| Metric | Formula |
|--------|---------|
| **ΔX** | `cx[t] − cx[t−1]` (horizontal pixel displacement) |
| **ΔY** | `cy[t] − cy[t−1]` (vertical pixel displacement, screen coords) |
| **Speed** | `√(ΔX² + ΔY²) × FPS` (pixels per second) |
| **Direction** | `atan2(−ΔY, ΔX)` → 8-way compass |
| **Total Distance** | `Σ √(ΔX² + ΔY²)` over all frames |
| **Net Displacement** | `(cx_last − cx_first, cy_last − cy_first)` |

---

## 🛠️ Customisation

- **Change YOLO model**: Edit `model_path` in `tracker.py` → use `yolov8s.pt`, `yolov8m.pt`, etc.
- **Different tracker**: Change `tracker="bytetrack.yaml"` to `"botsort.yaml"` in `tracker.py`
- **Confidence threshold**: Adjustable via the web UI slider
- **Port**: Change `port=5000` in `app.py`

---

*Built for the Vista Project — Object-Specific Movement Detection & Tracking*
