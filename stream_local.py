import os
import cv2
import time
import shutil
import boto3
import uvicorn
import requests
import tempfile
import subprocess
import threading
import numpy as np
import csv
from collections import deque
from ultralytics import YOLO
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

# ===================== Config =====================
S3_BUCKET = os.getenv("S3_BUCKET")
WS_ENDPOINT = os.getenv("WS_ENDPOINT")

if not S3_BUCKET or not WS_ENDPOINT:
    raise RuntimeError("Missing required environment variables.")


TARGET_FPS = 20
BUFFER_SECONDS = 5  # reduced buffer for faster alert delivery
MAX_ALERTS = 20
DETECTION_CLASS = "gun"
DETECTION_THRESH = 0.85  # higher confidence threshold
PRESIGN_EXPIRES = 86400  # 24h presigned URL

# CSV for latency logs
CSV_LOG = "latency_log.csv"
if not os.path.exists(CSV_LOG):
    with open(CSV_LOG, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["upload_ms", "ws_ms", "total_ms"])

# ===================== AWS / FastAPI =====================
s3 = boto3.client("s3")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"]
)

# ===================== FFmpeg discovery =====================
def resolve_ffmpeg():
    cand = []
    if shutil.which("ffmpeg"):
        cand.append(shutil.which("ffmpeg"))
    if os.getenv("FFMPEG_PATH"):
        cand.insert(0, os.getenv("FFMPEG_PATH"))
    cand += [
        r"C:\ProgramData\chocolatey\bin\ffmpeg.exe",
        r"C:\ProgramData\chocolatey\lib\ffmpeg\tools\ffmpeg\bin\ffmpeg.exe",
    ]
    for p in cand:
        if p and os.path.exists(p):
            return p
    return None

FFMPEG_EXE = resolve_ffmpeg()
print(f"[DEBUG] FFmpeg: {FFMPEG_EXE or 'NOT FOUND'}")

def run_ffmpeg(args: list):
    exe = FFMPEG_EXE or shutil.which("ffmpeg")
    if not exe or not os.path.exists(exe):
        raise RuntimeError("FFmpeg not found. Set FFMPEG_PATH or install FFmpeg.")
    subprocess.run([exe] + args, check=True)

# ===================== Model & Camera =====================
model = YOLO("best.pt")

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("[WARN] Could not open webcam. /video_feed will show 'No camera'.")
    cap = None

frame_buffer = deque(maxlen=int(TARGET_FPS * BUFFER_SECONDS))
alerts = []
alerts_lock = threading.Lock()

# ===================== Helpers =====================
def _even_dims(w, h):
    return (w // 2) * 2, (h // 2) * 2

def save_clip_and_upload(frames):
    """Encode frames to MP4 via FFmpeg and upload to S3."""
    if not frames:
        raise ValueError("No frames to save")

    h, w, _ = frames[0].shape
    width, height = _even_dims(w, h)
    if (w, h) != (width, height):
        frames = [cv2.resize(f, (width, height)) for f in frames]

    tmp_avi = tempfile.mktemp(suffix=".avi")
    avi_fourcc = cv2.VideoWriter_fourcc(*"MJPG")
    avi = cv2.VideoWriter(tmp_avi, avi_fourcc, TARGET_FPS, (width, height))
    if not avi.isOpened():
        raise RuntimeError("Failed to open MJPEG writer")
    for f in frames:
        avi.write(f)
    avi.release()

    tmp_mp4 = tempfile.mktemp(suffix=".mp4")
    try:
        run_ffmpeg([
            "-y", "-loglevel", "error",
            "-i", tmp_avi,
            "-c:v", "libx264",
            "-profile:v", "baseline", "-level", "3.0",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            "-r", str(TARGET_FPS),
            "-preset", "veryfast",
            "-crf", "23",
            "-an",
            tmp_mp4,
        ])
        output_path = tmp_mp4
    except subprocess.CalledProcessError as e:
        print(f"[ffmpeg] failed, fallback to mp4v: {e}")
        tmp_mp4 = tempfile.mktemp(suffix=".mp4")
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        wtr = cv2.VideoWriter(tmp_mp4, fourcc, TARGET_FPS, (width, height))
        if not wtr.isOpened():
            os.remove(tmp_avi)
            raise RuntimeError("mp4v writer also failed")
        for f in frames:
            wtr.write(f)
        wtr.release()
        output_path = tmp_mp4

    s3_key = f"clips/{int(time.time())}.mp4"
    s3.upload_file(output_path, S3_BUCKET, s3_key, ExtraArgs={"ContentType": "video/mp4"})

    for p in (tmp_avi, output_path):
        try:
            os.remove(p)
        except Exception:
            pass

    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": S3_BUCKET, "Key": s3_key},
        ExpiresIn=PRESIGN_EXPIRES
    )
    print("[DEBUG] Uploaded:", s3_key)
    print("[DEBUG] URL:", url)
    return url

def send_websocket_notification(alert):
    try:
        requests.post(WS_ENDPOINT, json=alert, timeout=1)
    except Exception as e:
        print(f"[WS] notify error: {e}")

# ===================== Detection Loop =====================
def detection_loop():
    if cap is None:
        return
    while True:
        ok, frame = cap.read()
        if not ok:
            time.sleep(0.01)
            continue

        frame_buffer.append(frame.copy())
        results = model(frame, verbose=False)

        for box in results[0].boxes:
            cls = model.names[int(box.cls[0])]
            conf = float(box.conf[0])

            if cls.lower() == DETECTION_CLASS and conf > DETECTION_THRESH:
                t_detect = time.time()
                frames_snapshot = list(frame_buffer)

                try:
                    t_before_upload = time.time()
                    clip_url = save_clip_and_upload(frames_snapshot)
                    t_after_upload = time.time()
                except Exception as e:
                    print(f"[clip] save/upload failed: {e}")
                    continue

                alert = {
                    "id": str(time.time()),
                    "type": cls,
                    "confidence": conf,
                    "timestamp": int(time.time() * 1000),
                    "presignedUrl": clip_url,
                }

                t_before_ws = time.time()
                send_websocket_notification(alert)
                t_after_ws = time.time()

                upload_latency = (t_after_upload - t_before_upload) * 1000
                ws_latency = (t_after_ws - t_before_ws) * 1000
                total_latency = (t_after_ws - t_detect) * 1000

                print(
                    f"[LATENCY] Total: {total_latency:.1f} ms "
                    f"(upload: {upload_latency:.1f} ms, ws: {ws_latency:.1f} ms)"
                )

                # Log to CSV
                try:
                    with open(CSV_LOG, mode="a", newline="") as f:
                        writer = csv.writer(f)
                        writer.writerow([f"{upload_latency:.1f}", f"{ws_latency:.1f}", f"{total_latency:.1f}"])
                except Exception as e:
                    print(f"[CSV] log write failed: {e}")

                with alerts_lock:
                    alerts.insert(0, alert)
                    if len(alerts) > MAX_ALERTS:
                        alerts.pop()

        time.sleep(1.0 / TARGET_FPS)

threading.Thread(target=detection_loop, daemon=True).start()

# ===================== Streaming & API =====================
def generate_frames():
    if cap is None:
        img = np.zeros((360, 640, 3), dtype=np.uint8)
        cv2.putText(img, "No camera detected", (50, 180),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2,
                    cv2.LINE_AA)
        while True:
            _, buffer = cv2.imencode(".jpg", img)
            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n")
    else:
        while True:
            ok, frame = cap.read()
            if not ok:
                time.sleep(0.01)
                continue
            results = model(frame, verbose=False)
            annotated = results[0].plot()
            _, buffer = cv2.imencode(".jpg", annotated)
            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n")

@app.get("/video_feed")
def video_feed():
    return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/alerts")
def get_alerts():
    with alerts_lock:
        return {"alerts": alerts}

@app.get("/test_clip")
def test_clip():
    h, w = 480, 640
    frames = []
    for i in range(TARGET_FPS * 3):
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        cv2.putText(frame, f"Frame {i+1}", (20, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2,
                    cv2.LINE_AA)
        frames.append(frame)
    url = save_clip_and_upload(frames)
    return {"url": url, "ffmpeg": FFMPEG_EXE or "NOT FOUND"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
