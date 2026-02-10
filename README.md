# 🛡️ Smart Surveillance System

An AI-powered surveillance system with real-time weapon detection using YOLOv8, featuring live video streaming, automated alerts (SMS/Email), and evidence management.

![Python](https://img.shields.io/badge/Python-3.9+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green)
![YOLOv8](https://img.shields.io/badge/YOLOv8-Latest-orange)
![License](https://img.shields.io/badge/License-MIT-yellow)

> **Developed by [Pranav Thanavel](https://github.com/pranav24547)**

## ✨ Features

- **🎯 Real-time Weapon Detection** - YOLOv8-based detection for guns, knives, rifles, and pistols
- **📹 Live Video Streaming** - WebSocket-based video stream with detection overlays
- **🚨 Automated Alerts** - SMS (Twilio) and Email notifications with cooldown logic
- **💾 Evidence Storage** - Automatic saving and organization of detection evidence
- **📊 Web Dashboard** - Modern, responsive dashboard for monitoring and management
- **⚙️ Configurable** - YAML-based configuration for easy customization

## 🏗️ Project Structure

```
smart-surveillance-system/
├── backend/
│   ├── main.py              # FastAPI server entry point
│   ├── config.py            # Configuration management
│   ├── detection/
│   │   ├── detector.py      # YOLOv8 weapon detector
│   │   └── processor.py     # Video frame processing
│   ├── alerts/
│   │   ├── alert_manager.py # Alert coordination
│   │   ├── sms_handler.py   # Twilio SMS integration
│   │   └── email_handler.py # SMTP email integration
│   └── storage/
│       └── evidence_manager.py # Evidence storage
├── frontend/
│   ├── index.html           # Dashboard HTML
│   ├── styles.css           # Dashboard styles
│   └── app.js               # Dashboard JavaScript
├── config.example.yaml      # Configuration template (copy to config.yaml)
├── config.yaml              # Your local config (git-ignored)
├── .gitignore               # Git ignore rules
├── requirements.txt         # Python dependencies
└── README.md
```

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Webcam or video source
- (Optional) CUDA-capable GPU for faster inference

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Pranav24547/smart-surveillance-system.git
   cd smart-surveillance-system
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   
   # Windows
   .\venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure the system**
   ```bash
   # Copy the template config
   copy config.example.yaml config.yaml   # Windows
   cp config.example.yaml config.yaml     # Linux/Mac
   ```
   Then edit `config.yaml` to customize:
   - Detection confidence threshold
   - Video source (webcam, file, RTSP)
   - Alert settings (Telegram/WhatsApp/SMS/Email)
   - Storage paths

   > ⚠️ **Never commit `config.yaml`** — it contains your secrets. It is already git-ignored.

5. **Run the backend**
   ```bash
   cd backend
   python main.py
   ```

6. **Open the dashboard**
   Open `frontend/index.html` in your browser, or serve it:
   ```bash
   cd frontend
   python -m http.server 3000
   ```
   Then visit `http://localhost:3000`

## ⚙️ Configuration

### config.yaml

```yaml
detection:
  model_path: "models/yolov8n.pt"  # Path to YOLO model
  confidence_threshold: 0.70        # Minimum confidence
  classes:
    - gun
    - knife
    - rifle
    - pistol

video:
  source: 0                         # 0=webcam, or path/URL
  frame_width: 640
  frame_height: 480
  fps: 30

alerts:
  enabled: true
  cooldown_seconds: 60              # Time between alerts
  
  sms:
    enabled: false
    twilio_account_sid: "YOUR_SID"
    twilio_auth_token: "YOUR_TOKEN"
    from_number: "+1234567890"
    to_numbers:
      - "+0987654321"
    
  email:
    enabled: false
    smtp_server: "smtp.gmail.com"
    smtp_port: 587
    sender_email: "your-email@gmail.com"
    sender_password: "your-app-password"
    recipients:
      - "security@example.com"

storage:
  evidence_path: "data/evidence"
  max_evidence_files: 1000
  save_annotated_frames: true

server:
  host: "0.0.0.0"
  port: 8000
```

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ws/stream` | WebSocket | Live video stream with detections |
| `/api/status` | GET | System status and statistics |
| `/api/detections` | GET | Recent detection records |
| `/api/alerts` | GET | Alert history |
| `/api/evidence/{id}` | GET | Get evidence image |
| `/api/config` | POST | Update runtime configuration |
| `/api/alerts/test` | POST | Send test alert |
| `/api/alerts/reset-cooldown` | POST | Reset alert cooldown |

## 🧠 Training Custom Model

For production use, train YOLOv8 on a weapon dataset:

1. **Prepare dataset** in YOLO format:
   ```
   dataset/
   ├── train/
   │   ├── images/
   │   └── labels/
   └── val/
       ├── images/
       └── labels/
   ```

2. **Create data.yaml**:
   ```yaml
   train: dataset/train/images
   val: dataset/val/images
   nc: 4
   names: ['gun', 'knife', 'rifle', 'pistol']
   ```

3. **Train model**:
   ```python
   from ultralytics import YOLO
   
   model = YOLO('yolov8n.pt')
   model.train(data='data.yaml', epochs=100, imgsz=640)
   ```

4. **Use trained model**:
   Update `config.yaml`:
   ```yaml
   detection:
     model_path: "runs/detect/train/weights/best.pt"
   ```

## 🖥️ Dashboard Features

- **Dashboard View** - Overview with stats and quick preview
- **Live Feed** - Full-screen video with real-time detection overlay
- **Alerts** - Complete alert history with filtering
- **Evidence** - Gallery of captured detection images
- **Settings** - Runtime configuration adjustments

## 🔒 Security Notes

- Never commit credentials to version control
- Use environment variables for sensitive data
- For Gmail, use App Passwords (not regular password)
- Consider rate limiting in production
- Add authentication for production deployment

## 📋 Roadmap

- [ ] Multiple camera support
- [ ] Face recognition integration
- [ ] Behavior analysis
- [ ] Mobile app companion
- [ ] Cloud deployment options
- [ ] Historical analytics dashboard

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## ⚠️ Disclaimer

This system is intended for educational and authorized security purposes only. Always comply with local laws and regulations regarding surveillance systems.

## 👨‍💻 Author

**Pranav Thanavel** — [GitHub](https://github.com/pranav24547)

---

⭐ If you find this project helpful, consider giving it a star on GitHub!
