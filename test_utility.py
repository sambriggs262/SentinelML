from ultralytics import YOLO
import os

def test_model(model_path: str, image_path:str, confidence: int) -> None:
    """Tests a given model on an image or video given a confidence level."""
    if not os.path.exists(model_path):
        print("Error: model path does not exist.")
        return
    elif not os.path.exists(image_path):
        print("Error: image/video path does not exist.")
        return
    print("Loading model...")
    model = YOLO(model_path)
    print("Model loaded")
    print("Evaluating...")
    results = model(image_path, device=0, save=True, conf = confidence)
    print("Complete!")
