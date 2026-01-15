import os
import shutil
import yaml

# Paths to your YOLOv8 datasets
dataset_a_path = "path_to_dataset_a"  # Update with Dataset A path
dataset_b_path = "path_to_dataset_b"  # Update with Dataset B path
merged_dataset_path = "path_to_merged_dataset"  # Update with desired output path

# Define class remapping (e.g., "firearm" -> "gun")
class_remap = {
    "firearm": "gun",  # Remap "firearm" to "gun"
    "weapon": "gun",   # Add other similar classes if necessary
}

def load_yaml(file_path):
    """Load a YOLO data.yaml file."""
    with open(file_path, "r") as file:
        return yaml.safe_load(file)

def save_yaml(data, file_path):
    """Save a YOLO data.yaml file."""
    with open(file_path, "w") as file:
        yaml.safe_dump(data, file)

def remap_labels(label_file, class_map):
    """Remap class labels in a YOLOv8 label file."""
    with open(label_file, "r") as file:
        lines = file.readlines()

    updated_lines = []
    for line in lines:
        parts = line.strip().split()
        class_id = int(parts[0])
        if class_id in class_map:
            class_id = class_map[class_id]  # Map the class ID to the new one
        updated_lines.append(f"{class_id} " + " ".join(parts[1:]) + "\n")

    with open(label_file, "w") as file:
        file.writelines(updated_lines)

def merge_yolo_datasets(dataset_a, dataset_b, output_path, remap):
    """Merge two YOLOv8 datasets."""
    # Load dataset YAML files
    data_a = load_yaml(os.path.join(dataset_a, "data.yaml"))
    data_b = load_yaml(os.path.join(dataset_b, "data.yaml"))

    # Combine class names and create a unified class list
    combined_classes = list(set(data_a["names"] + data_b["names"]))
    class_map = {name: combined_classes.index(remap.get(name, name)) for name in combined_classes}

    # Create directories for the merged dataset
    for subdir in ["images/train", "images/val", "images/test", "labels/train", "labels/val", "labels/test"]:
        os.makedirs(os.path.join(output_path, subdir), exist_ok=True)

    # Function to copy and remap files
    def copy_and_remap(src_images, src_labels, dst_images, dst_labels):
        for file_name in os.listdir(src_images):
            # Copy image
            shutil.copy(os.path.join(src_images, file_name), os.path.join(dst_images, file_name))
            # Copy and remap label
            label_file = os.path.splitext(file_name)[0] + ".txt"
            src_label_path = os.path.join(src_labels, label_file)
            if os.path.exists(src_label_path):
                dst_label_path = os.path.join(dst_labels, label_file)
                shutil.copy(src_label_path, dst_label_path)
                remap_labels(dst_label_path, class_map)

    # Merge training data
    copy_and_remap(
        os.path.join(dataset_a, "images/train"),
        os.path.join(dataset_a, "labels/train"),
        os.path.join(output_path, "images/train"),
        os.path.join(output_path, "labels/train"),
    )
    copy_and_remap(
        os.path.join(dataset_b, "images/train"),
        os.path.join(dataset_b, "labels/train"),
        os.path.join(output_path, "images/train"),
        os.path.join(output_path, "labels/train"),
    )

    # Merge validation data
    copy_and_remap(
        os.path.join(dataset_a, "images/val"),
        os.path.join(dataset_a, "labels/val"),
        os.path.join(output_path, "images/val"),
        os.path.join(output_path, "labels/val"),
    )
    copy_and_remap(
        os.path.join(dataset_b, "images/val"),
        os.path.join(dataset_b, "labels/val"),
        os.path.join(output_path, "images/val"),
        os.path.join(output_path, "labels/val"),
    )

    # Merge test data
    copy_and_remap(
        os.path.join(dataset_a, "images/test"),
        os.path.join(dataset_a, "labels/test"),
        os.path.join(output_path, "images/test"),
        os.path.join(output_path, "labels/test"),
    )
    copy_and_remap(
        os.path.join(dataset_b, "images/test"),
        os.path.join(dataset_b, "labels/test"),
        os.path.join(output_path, "images/test"),
        os.path.join(output_path, "labels/test"),
    )

    # Save the combined YAML file
    save_yaml({"path": output_path, "names": combined_classes}, os.path.join(output_path, "data.yaml"))

# Merge datasets
merge_yolo_datasets(dataset_a_path, dataset_b_path, merged_dataset_path, class_remap)

print(f"Merged dataset saved to: {merged_dataset_path}")
