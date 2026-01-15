import train_utility

if __name__ == "__main__":
    model = str(input("Enter a model path: "))
    save = str(input("Enter the location to save the model in ONNX"))
    epochs = float(input("Enter a number of epochs:"))
    train_utility.train(model, save, epochs)