import os
import flwr as fl
import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, transforms
from torch.utils.data import DataLoader, Subset


# ---- Modelo ----
class SimpleCNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(1, 8, 3), nn.ReLU(),
            nn.MaxPool2d(2),
        )
        self.fc = nn.Sequential(
            nn.Linear(8 * 13 * 13, 64), nn.ReLU(),
            nn.Linear(64, 10),
        )

    def forward(self, x):
        return self.fc(self.conv(x).view(x.size(0), -1))


# ---- Configuração do cliente ----
CLIENT_ID = int(os.getenv("CLIENT_ID", "0"))
NUM_CLIENTS = int(os.getenv("NUM_CLIENTS", "3"))
SERVER_ADDRESS = os.getenv("SERVER_ADDRESS", "server:8080")


# ---- Partição IID do MNIST ----
# Cada cliente recebe um subconjunto disjunto do dataset, baseado em CLIENT_ID.
# Isto simula dados privados por hospital sem precisar de 3 datasets distintos.
def get_client_loader():
    transform = transforms.ToTensor()
    full_trainset = datasets.MNIST(
        "/data", train=True, download=True, transform=transform
    )

    n = len(full_trainset)
    # determinístico mas aleatório (mesma seed em todos os clientes -> partição consistente)
    g = torch.Generator().manual_seed(42)
    perm = torch.randperm(n, generator=g).tolist()

    shard_size = n // NUM_CLIENTS
    start = CLIENT_ID * shard_size
    end = start + shard_size if CLIENT_ID < NUM_CLIENTS - 1 else n
    indices = perm[start:end]

    subset = Subset(full_trainset, indices)
    print(f"[Cliente {CLIENT_ID}] {len(subset)} amostras de treino", flush=True)
    return DataLoader(subset, batch_size=32, shuffle=True)


trainloader = get_client_loader()

model = SimpleCNN()
optimizer = optim.SGD(model.parameters(), lr=0.01)
criterion = nn.CrossEntropyLoss()


# ---- Cliente Flower ----
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
        loss, correct, total = 0.0, 0, 0
        with torch.no_grad():
            for images, labels in trainloader:
                output = model(images)
                loss += criterion(output, labels).item()
                correct += (output.argmax(1) == labels).sum().item()
                total += labels.size(0)
        return loss, total, {"accuracy": correct / total}


# API moderna (não-deprecated)
fl.client.start_client(
    server_address=SERVER_ADDRESS,
    client=HospitalClient().to_client(),
)