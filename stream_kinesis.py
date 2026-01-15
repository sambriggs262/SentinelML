import cv2
import numpy as np
import subprocess
import os
import sys
from ultralytics import YOLO
from dotenv import load_dotenv

# --- Load environment ---
load_dotenv()
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
STREAM_NAME = os.getenv("KINESIS_STREAM_NAME", "sentinel-edge-stream")
MODEL_PATH = os.getenv("MODEL_PATH", "best.pt")

# --- YOLO Model ---
model = YOLO(MODEL_PATH)

# --- GStreamer pipeline using appsrc ---
gst_pipeline = (
    f"appsrc ! videoconvert ! x264enc tune=zerolatency bitrate=512 speed-preset=superfast "
    f"! kvssink stream-name={STREAM_NAME} aws-region={AWS_REGION}"
)

# Open a GStreamer process with stdin as appsrc input
gst_process = subprocess.Popen(
    ["gst-launch-1.0", "appsrc", "!", "videoconvert", "!", 
     "x264enc", "tune=zerolatency", "bitrate=512", "speed-preset=superfast", 
     "!", "kvssink", f"stream-name={STREAM_NAME}", f"aws-region={AWS_REGION}"],
    stdin=subprocess.PIPE
)

# --- Video capture ---
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    raise RuntimeError("Could not open webcam")

print("[INFO] YOLO detection + streaming started... Press 'q' to quit")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Resize for consistent processing
    frame = cv2.resize(frame, (640, 480))

    # YOLO detection
    results = model(frame)
    annotated_frame = results[0].plot()

    # Encode to JPEG and send to GStreamer stdin
    ret, buf = cv2.imencode(".jpg", annotated_frame)
    if ret:
        gst_process.stdin.write(buf.tobytes())

    # Display locally
    cv2.imshow("SentinelML YOLO Stream", annotated_frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# --- Cleanup ---
cap.release()
cv2.destroyAllWindows()
gst_process.stdin.close()
gst_process.terminate()
print("[INFO] Streaming stopped.")
