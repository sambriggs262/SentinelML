from datetime import datetime
import json
import os
from ultralytics import YOLO
from comet_ml import Experiment
from dotenv import load_dotenv

load_dotenv()

def train(model_path: str, save: str, epochs: int) -> None:
    experiment = Experiment(
        api_key=os.getenv("COMET_API_KEY"),
        project_name=os.getenv("COMET_PROJECT_NAME"),
        workspace=os.getenv("COMET_WORKSPACE")
    )

    experiment.log_parameters({
        "model_path": model_path,
        "save_path": save,
        "epochs": epochs
    })

    model = YOLO(model_path)

    model.train(
        data=os.getenv("DATASET_YAML", "data.yaml"),

        epochs=epochs,
        save_dir=save
    )

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    results_dir = os.path.join(save, "results", timestamp)
    os.makedirs(results_dir, exist_ok=True)

    val_results = model.val()
    experiment.log_metrics({
        "val_precision": val_results.box.p,
        "val_recall": val_results.box.r,
        "val_map50": val_results.box.map50,
        "val_map": val_results.box.map
    })
    with open(os.path.join(results_dir, "val_results.json"), "w") as f:
        json.dump(val_results, f, indent=4)

    test_results = model.val(split='test')
    experiment.log_metrics({
        "test_precision": test_results.box.p,
        "test_recall": test_results.box.r,
        "test_map50": test_results.box.map50,
        "test_map": test_results.box.map
    })
    with open(os.path.join(results_dir, "test_results.json"), "w") as f:
        json.dump(test_results, f, indent=4)

    model.export(format="onnx")
    onnx_path = os.path.join(save, "weights", "best.onnx")
    if os.path.exists(onnx_path):
        experiment.log_model("onnx_model", onnx_path)

    print(f"\nResults saved to {results_dir}")
