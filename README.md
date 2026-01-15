# SentinelML

A modular, open-source framework for real-time firearm detection and alerting using YOLOv8 and cloud-native infrastructure.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Next.js](https://img.shields.io/badge/frontend-Next.js-black)](https://nextjs.org/)

---

## Overview

SentinelML is a research-oriented system designed to evaluate the effectiveness of an AI-driven, real-time, direct-to-operator firearm detection system developed using open-source models and cloud-native infrastructure. This project seeks to explore whether recent advances in open-source computer vision and cloud tooling can enable a lower-cost, practical firearm detection framework for research and educational purposes.

The framework prioritizes three distinct criteria: speed, reliability, and reduction of third-party human monitoring latency. By leveraging YOLOv8 for detection, FastAPI for inference, and AWS services for alert delivery, SentinelML achieved a mean latency from detection to alert of 301 milliseconds under experimental conditions, demonstrating response capabilities suitable for real-time security monitoring.

**Key Features:**
- YOLOv8-based firearm detection with configurable confidence thresholds
- Real-time web dashboard with alert visualization and video playback
- Direct alert delivery via WebSocket with presigned S3 URLs for video clips
- Dataset merging and preprocessing utilities
- Experiment tracking integration (Comet ML)
- Data privacy through local inference and VPC-isolated infrastructure

---

## Important Notices

### Research and Educational Use Only

This project is intended for **academic research and educational evaluation only**. It is not a replacement for enterprise firearm detection platforms and should not be deployed in operational settings without proper legal, ethical, and institutional review.

The system demonstrates that cost-efficient, open-source tools can achieve competitive performance characteristics suitable for research, education, and constrained deployment contexts, but it lacks enterprise-level security integrations required by larger agencies.

### Dataset

The custom dataset used in this research combines the YouTube Gun Detection Dataset (YouTubeGDD) with supplementary custom video footage. The YouTubeGDD was selected for its rich contextual information and dual person-gun labels. Custom footage was recorded to address dataset limitations in perspective (adding downward, ceiling-mounted angles typical of CCTV) and resolution (reducing from 1440p/4K to 720p to match typical security footage).

The complete custom dataset is not publicly released due to privacy and safety considerations. However, all training, augmentation, and evaluation code is fully reproducible with any YOLO-formatted dataset.

---

## System Architecture

```
┌──────────────────────────────────────────────────────────┐
│                  LOCAL INFRASTRUCTURE                    │
│                                                          │
│  ┌─────────────┐         ┌──────────────────┐          │
│  │   Webcam    │────────>│  YOLOv8 + FastAPI│          │
│  │   Input     │         │  (stream_local)  │          │
│  └─────────────┘         └────────┬─────────┘          │
│                                   │                    │
│                    ┌──────────────┴──────────────┐     │
│                    │                             │     │
│              ┌─────▼──────┐            ┌────────▼───┐ │
│              │   MJPEG    │            │  10s Frame │ │
│              │   Stream   │            │  Buffer    │ │
│              └─────┬──────┘            └────────┬───┘ │
│                    │                            │     │
│                    │              Detection     │     │
│                    │              Triggered    │     │
│                    │                            │     │
│                    │                   ┌────────▼───┐ │
│                    │                   │ MP4 Encode │ │
│                    │                   │ & Upload   │ │
│                    │                   └────────┬───┘ │
└────────────────────┼───────────────────────────┼──────┘
                     │                           │
                     │                           │
         ┌───────────┴─────────────┐    ┌────────▼──────────────┐
         │                         │    │                       │
         ▼                         ▼    ▼                       ▼
    ┌─────────────┐          ┌──────────────┐          ┌────────────┐
    │   Frontend  │          │ AWS Lambda   │          │  AWS S3    │
    │  Dashboard  │          │  (Detection) │          │  (Clips)   │
    │  (localhost:│          │              │          │            │
    │   3000)     │          └──────────────┘          └────────────┘
    └─────────────┘                  
                         
```

**System Flow:**

1. **Local Inference (Always On-Device)**: YOLOv8 model runs continuously on a local machine via FastAPI (`stream_local.py`), processing frames from a webcam or video input. Frames are annotated with bounding boxes and streamed via MJPEG to the frontend dashboard and stored in a 10-second rolling buffer.

2. **Detection Trigger**: When a frame contains a firearm detection exceeding the configured confidence threshold (default 0.85), the system:
   - Encodes the last 10 seconds of buffered frames into an MP4 video clip
   - Uploads the clip to AWS S3 with a presigned URL
   - Invokes AWS Lambda with detection metadata

3. **AWS Alert Pipeline**: Lambda receives the detection event and:
   - Forwards the alert via WebSocket to connected dashboard clients

4. **Frontend Dashboard**: React.js-based web interface displays:
   - Real-time MJPEG stream from local inference
   - Recent alerts with detection metadata
   - Video playback of detection clips via presigned S3 URLs

**Key Design Features:**
- All inference runs locally; no video or raw frames sent to AWS
- Data privacy maintained through on-device processing
- Low latency achieved through direct local-to-AWS communication
- Scalability for multi-camera deployments through independent Lambda invocations per detection event

---

## Quick Start

### Requirements
- Python 3.8+ with pip
- Node.js 18+ (for dashboard)
- CUDA 11.8+ (recommended for GPU inference)
- FFmpeg (for video encoding)

### Local Setup (No AWS Required)

#### 1. Clone Repository
```bash
git clone https://github.com/sambriggs262/SentinelML.git
cd SentinelML
```

#### 2. Python Environment
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### 3. Configure Dataset
Prepare a YOLO-formatted dataset (organized as `images/{train,val,test}` and `labels/{train,val,test}`), then update `data.yaml`:

```yaml
train: /path/to/your/dataset/images/train
val: /path/to/your/dataset/images/val
test: /path/to/your/dataset/images/test

nc: 2
names:
  - person
  - gun
```

#### 4. Train Model (Optional)
```bash
python train.py
# Prompts for: model path, save location, number of epochs
# Logs metrics to Comet ML if COMET_API_KEY is set
```

The YOLOv8 model was trained using PyTorch CUDA/cuDNN with the following configuration:
- 50 epochs on NVIDIA GPU
- Batch size: 16
- Learning rate: 0.0016
- Optimizer: AdamW with adaptive learning rates
- Loss function: Focal Loss (to address class imbalance)
- Final metrics: mAP@50=0.91, mAP@50-95=0.72, Precision=0.94, Recall=0.86

#### 5. Run Local Inference
```bash
python stream_local.py
```

The system:
- Opens webcam stream with real-time YOLO detections
- Buffers the last 10 seconds of frames in memory
- Serves dashboard API on `http://localhost:8000`
- Achieves mean latency of approximately 301 ms from detection to alert
- Available endpoints:
  - `/video_feed` – MJPEG stream of annotated frames
  - `/alerts` – Recent alert history with presigned S3 URLs
  - `/test_clip` – Test video encoding pipeline

#### 6. Dashboard (New Terminal)
```bash
cd dashboard
npm install
cp .env.local.example .env.local
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The dashboard displays:
- Live YOLO feed with real-time bounding boxes
- Recent alerts with detection metadata
- Expandable alert details with 10-second video playback

---

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# AWS Configuration (optional, only needed for cloud deployment)
AWS_REGION=us-east-1
S3_BUCKET=your-s3-bucket-name
WS_ENDPOINT=wss://your-api-gateway-url.execute-api.region.amazonaws.com/stage

# YOLO Model Path
MODEL_PATH=best.pt

# Kinesis Stream
KINESIS_STREAM_NAME=sentinel-edge-stream

# Comet ML (optional, for experiment tracking)
COMET_API_KEY=your-comet-api-key
COMET_PROJECT_NAME=sentinel-ml
COMET_WORKSPACE=your-workspace

# FFmpeg (Windows only)
# FFMPEG_PATH=C:\path\to\ffmpeg.exe

# Dataset
DATASET_YAML=data.yaml
```

**Note:** Never commit `.env` files. Use `.env.example` for documentation.

### Inference Parameters

Edit `stream_local.py` or `stream_kinesis.py` to adjust:

```python
TARGET_FPS = 20                      # Output frame rate
BUFFER_SECONDS = 5                   # Seconds of video to buffer before detection
DETECTION_CLASS = "gun"              # Class name to trigger alerts
DETECTION_THRESH = 0.85              # Confidence threshold (0-1)
PRESIGN_EXPIRES = 86400              # S3 presigned URL validity (seconds)
```

---

## AWS Deployment

### Prerequisites
- AWS account with appropriate IAM permissions
- S3 bucket for video storage
- API Gateway WebSocket endpoint

### Manual Setup

1. **S3 Bucket**
   ```bash
    aws s3 mb s3://<your-bucket-name> --region us-east-1
   ```

2. **IAM Role**
   Attach policy allowing S3 uploads and presigned URL generation.

3. **API Gateway WebSocket**
   Create a WebSocket API with Lambda integrations for connection management.

4. **Environment Configuration**
   ```bash
   export AWS_REGION=us-east-1
   export S3_BUCKET=<your-bucket-name>

   export WS_ENDPOINT=wss://your-api-id.execute-api.us-east-1.amazonaws.com/prod
   ```

5. **Run Cloud Pipeline**
   ```bash
   python stream_kinesis.py
   ```

### Cost Considerations
- S3 storage: ~$0.023 per GB/month
- API Gateway: ~$3.50 per million WebSocket messages
- Bandwidth: Variable (typically <$0.01/GB for intra-region)
- Compute: Depends on inference frequency

This cost structure makes the framework feasible for adoption by small organizations and institutions that cannot sustain the infrastructure costs of enterprise solutions.

---

## Dataset Management

### YOLO Dataset Format
```
dataset/
├── images/
│   ├── train/
│   ├── val/
│   └── test/
└── labels/
    ├── train/
    ├── val/
    └── test/
```

Label format: One `.txt` file per image
```
<class_id> <x_center> <y_center> <width> <height>
```

### Dataset Augmentation
The YouTubeGDD images were augmented using the Python Albumentations library to address perspective and resolution mismatches. Augmentations applied:
- Simulated compression
- Contrast and brightness adjustments
- Distortion effects
- Downsampling to 720p to match typical CCTV footage

### Merging Datasets
Combine multiple datasets with class remapping:

```bash
python merge_Datasets.py
```

Edit the script to specify:
- `dataset_a_path` and `dataset_b_path`
- `merged_dataset_path`
- Class remappings (e.g., "firearm" → "gun")

---

## Performance and Results

### Model Metrics

The trained YOLOv8 model achieved the following performance on the validation dataset:

| Metric | Value |
|--------|-------|
| Mean Average Precision @ IoU 0.5 (mAP@50) | 0.91 |
| Mean Average Precision @ IoU 0.5-0.95 (mAP@50-95) | 0.72 |
| Precision | 0.94 |
| Recall | 0.86 |
| Box Loss (final) | 0.2728 |

The mAP@50 metric demonstrates effective detection at moderate overlap thresholds, while mAP@50-95 reflects performance under stricter localization requirements. Precision of 0.94 indicates low false positive rates, while recall of 0.86 confirms balanced sensitivity for true positive detection.

### System Latency

Mean end-to-end latency under experimental conditions (detection to alert display): **301 milliseconds**

This includes:
- YOLO inference: ~35-50 ms
- Video encoding and S3 upload: ~150-250 ms
- WebSocket notification: <10 ms
- Frontend display: <50 ms

This latency supports the feasibility of the framework for critical firearm detection tasks where reduced alert latency meaningfully improves response effectiveness.

### Training Configuration

Model training was conducted on an NVIDIA RTX 2060 GPU with the following configuration:
- 50 training epochs
- Batch size: 16
- Learning rate: 0.0016
- Optimizer: AdamW with adaptive per-parameter learning rates
- Loss function: Focal Loss to address class imbalance between person and gun categories

---

## API Reference

### Local Inference Endpoints

#### GET `/video_feed`
Returns MJPEG stream of real-time annotated frames.

**Response:** 200 OK (MJPEG stream)

```bash
curl http://localhost:8000/video_feed --output stream.mjpeg
```

#### GET `/alerts`
Returns recent detection alerts with presigned S3 URLs.

**Response:** 200 OK (JSON)

```json
{
  "alerts": [
    {
      "id": "1704067200.123",
      "type": "gun",
      "confidence": 0.92,
      "timestamp": 1704067200123,
      "presignedUrl": "https://s3.amazonaws.com/..."
    }
  ]
}
```

#### GET `/test_clip`
Tests video encoding and upload pipeline.

**Response:** 200 OK (JSON)

```json
{
"url": "https://s3.amazonaws.com/<your-bucket-name>/clips/1704067200.mp4"
  "ffmpeg": "/usr/bin/ffmpeg"
}
```

---

## Limitations and Future Work

### Current Limitations
- Trained on a relatively small custom dataset, which may limit generalization across diverse environments
- Limited environmental testing; variations in lighting, weather, and camera quality not extensively evaluated
- Lacks enterprise-level security integrations required by larger agencies
- Single-camera configuration; no support for multi-camera systems

### Future Improvements
- Deploy detection loop on AWS EC2 or Lambda for full cloud-based processing and scalability
- Expand support for multi-camera systems to improve coverage and situational awareness
- Conduct extensive false positive rate testing during live deployment
- Explore newer model architectures such as DETR (DEtection TRansformer) for improved accuracy and efficiency
- Implement enterprise-level security integrations and compliance controls

---

## Troubleshooting

### No Camera Detected
```
[WARN] Could not open webcam. /video_feed will show 'No camera'.
```

**Solution:** Ensure camera is connected and not in use by another application.

### FFmpeg Not Found
```
RuntimeError: FFmpeg not found. Set FFMPEG_PATH or install FFmpeg.
```

**Solution:**
- macOS: `brew install ffmpeg`
- Ubuntu: `sudo apt-get install ffmpeg`
- Windows: Set `FFMPEG_PATH` environment variable

### AWS Credentials Error
```
botocore.exceptions.NoCredentialsError: Unable to locate credentials
```

**Solution:** Configure AWS credentials:
```bash
aws configure
# or export AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY
```

### Dashboard Connection Error
```
Error loading alerts. Is the Python backend running at http://localhost:8000?
```

**Solution:** Ensure `stream_local.py` or `stream_kinesis.py` is running before starting the dashboard.

---

## Development

### Running Tests
```bash
# Test YOLO model inference
python test.py

# Run training with small dataset (debugging)
python train.py  # Enter small dataset path
```

### Adding Custom Detection Classes
1. Update `data.yaml` with new class names
2. Retrain model: `python train.py`
3. Update `DETECTION_CLASS` in inference scripts

### Monitoring Experiments
Comet ML integration automatically logs:
- Training metrics (loss, mAP, precision, recall)
- Model checkpoints
- Hyperparameters

---

## Security & Privacy

### No Sensitive Data in Repository
- No AWS credentials committed
- No API keys in source code
- No personal dataset paths
- All credentials via environment variables

### Data Privacy and Control
- Video clips are never sent to external companies; data remains in user-controlled infrastructure
- System can run in complete isolation within a Virtual Private Cloud (VPC)
- Direct alert delivery to trained operators (dispatchers, officers) rather than third-party monitors
- S3 presigned URLs expire after 24 hours (configurable) to limit access duration

### Responsible Use Requirements
- Obtain proper consent before deploying in monitored environments
- Review applicable laws and regulations (varies by jurisdiction)
- Do not deploy in operational settings without legal, ethical, and institutional review
- This is research software, not approved for operational deployment

---

## Citation

If referencing this work in academic writing, please cite as:

```bibtex
@misc{sentinelml2026,
  title={SentinelML Real-Time Firearm Detection: A Cloud-Native Alternative to Commercial Solutions},
  author={Briggs, Sam},
  year={2026},
  note={Undergraduate Research Project, Department of Computer Science, James Madison University},
  howpublished={\url{https://github.com/sambriggs262/SentinelML}}
}
```

---

## License

This project is released under the MIT License. See [LICENSE](LICENSE) for details.

---

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

For major changes, please open an issue first to discuss proposed changes.

---

## Acknowledgments

- Ultralytics YOLOv8 for the detection model architecture and training framework
- YouTube Gun Detection Dataset (YouTubeGDD) as the primary dataset source
- FastAPI for the inference server framework
- Next.js for the frontend dashboard framework
- AWS Services for cloud infrastructure
- Dr. Nathan Sprague, James Madison University, for research supervision

---

## Contact & Support

- **Issues:** [GitHub Issues](https://github.com/sambriggs262/SentinelML/issues)
- **Email:** brigg2se@dukes.jmu.edu
- **Research Advisor:** Dr. Nathan Sprague, James Madison University

---

**Last Updated:** January 2026  
**Author:** Sam Briggs ([@sambriggs262](https://github.com/sambriggs262))  
**Affiliation:** Department of Computer Science, James Madison University
