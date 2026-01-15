import test_utility

if __name__ == "__main__":
    model = input("Enter YOLO model path: ")
    video = input("Enter video file path: ")
    conf = float(input("Enter confidence threshold (0-1): "))
    stream_name = input("Enter Kinesis stream name: ")

    test_utility.stream_and_detect(model, video, conf, stream_name)
