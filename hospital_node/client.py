import os
import numpy as np
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


# ---- Configuração ----
CLIENT_ID = int(os.getenv("CLIENT_ID", "0"))
NUM_CLIENTS = int(os.getenv("NUM_CLIENTS", "3"))
SERVER_ADDRESS = os.getenv("SERVER_ADDRESS", "server:8080")
PARTITION_MODE = os.getenv("PARTITION_MODE", "iid").lower()  # "iid" ou "dirichlet"
DIRICHLET_ALPHA = float(os.getenv("DIRICHLET_ALPHA", "0.5"))
SEED = 42


# ---- Particionamento ----
def iid_partition(num_samples, num_clients, seed):
    rng = np.random.default_rng(seed)
    perm = rng.permutation(num_samples)
    return np.array_split(perm, num_clients)


def dirichlet_partition(targets, num_clients, alpha, seed):
    """
    Para cada classe, amostra uma proporção Dirichlet(alpha) sobre os clientes
    e distribui as amostras dessa classe segundo essa proporção.
    Standard em literatura de FL non-IID (Hsu et al., 2019).
    """
    rng = np.random.default_rng(seed)
    targets = np.array(targets)
    num_classes = int(targets.max()) + 1
    client_idx = [[] for _ in range(num_clients)]

    for c in range(num_classes):
        idx_c = np.where(targets == c)[0]
        rng.shuffle(idx_c)
        proportions = rng.dirichlet([alpha] * num_clients)
        # cumulativos para fazer split
        cuts = (np.cumsum(proportions) * len(idx_c)).astype(int)[:-1]
        for i, split in enumerate(np.split(idx_c, cuts)):
            client_idx[i].extend(split.tolist())

    return [np.array(ix) for ix in client_idx]


def get_loaders():
    transform = transforms.ToTensor()
    trainset = datasets.MNIST("/data", train=True, download=True, transform=transform)
    testset = datasets.MNIST("/data", train=False, download=True, transform=transform)

    if PARTITION_MODE == "dirichlet":
        partitions = dirichlet_partition(
            trainset.targets.numpy(), NUM_CLIENTS, DIRICHLET_ALPHA, SEED
        )
    else:
        partitions = iid_partition(len(trainset), NUM_CLIENTS, SEED)

    my_indices = partitions[CLIENT_ID]
    subset = Subset(trainset, my_indices)

    # Logging útil: distribuição de classes neste cliente
    targets = np.array(trainset.targets)[my_indices]
    class_counts = np.bincount(targets, minlength=10)
    print(
        f"[Cliente {CLIENT_ID}] modo={PARTITION_MODE} "
        f"alpha={DIRICHLET_ALPHA if PARTITION_MODE == 'dirichlet' else '-'} "
        f"n_amostras={len(subset)}",
        flush=True,
    )
    print(f"[Cliente {CLIENT_ID}] classes: {class_counts.tolist()}", flush=True)

    train_loader = DataLoader(subset, batch_size=32, shuffle=True)
    # Avaliação: cada cliente avalia no conjunto de teste GLOBAL,
    # para medir generalização do modelo agregado, não desempenho local.
    test_loader = DataLoader(testset, batch_size=128, shuffle=False)
    return train_loader, test_loader


trainloader, testloader = get_loaders()

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
            for images, labels in testloader:
                output = model(images)
                loss += criterion(output, labels).item()
                correct += (output.argmax(1) == labels).sum().item()
                total += labels.size(0)
        return loss, total, {"accuracy": correct / total}


fl.client.start_client(
    server_address=SERVER_ADDRESS,
    client=HospitalClient().to_client(),
)