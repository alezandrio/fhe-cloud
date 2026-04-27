import flwr as fl
import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, transforms
from torch.utils.data import DataLoader
import os

# Simple CNN model
class SimpleCNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(1, 8, 3), nn.ReLU(),
            nn.MaxPool2d(2)
        )
        self.fc = nn.Sequential(
            nn.Linear(8 * 13 * 13, 64), nn.ReLU(),
            nn.Linear(64, 10)
        )

    def forward(self, x):
        return self.fc(self.conv(x).view(x.size(0), -1))

# Load MNIST
transform = transforms.ToTensor()
trainset = datasets.MNIST("/data", train=True, download=True, transform=transform)
trainloader = DataLoader(trainset, batch_size=32, shuffle=True)

model = SimpleCNN()
optimizer = optim.SGD(model.parameters(), lr=0.01)
criterion = nn.CrossEntropyLoss()

# Flower client
class HospitalClient(fl.client.NumPyClient):
    def get_parameters(self, config):
        return [p.detach().numpy() for p in model.parameters()]

    def set_parameters(self, parameters):
        for p, new_p in zip(model.parameters(), parameters):
            p.data = torch.tensor(new_p)

    def fit(self, parameters, config):
        self.set_parameters(parameters)
        model.train()
        for images, labels in trainloader:
            optimizer.zero_grad()
            loss = criterion(model(images), labels)
            loss.backward()
            optimizer.step()
        return self.get_parameters(config={}), len(trainloader.dataset), {}

    def evaluate(self, parameters, config):
        self.set_parameters(parameters)
        model.eval()
        loss, correct = 0, 0
        with torch.no_grad():
            for images, labels in trainloader:
                output = model(images)
                loss += criterion(output, labels).item()
                correct += (output.argmax(1) == labels).sum().item()
        return loss, len(trainloader.dataset), {"accuracy": correct / len(trainloader.dataset)}

server_address = os.getenv("SERVER_ADDRESS", "server:8080")
fl.client.start_numpy_client(server_address=server_address, client=HospitalClient())
