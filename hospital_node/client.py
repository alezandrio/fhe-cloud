import os
import numpy as np
import flwr as fl
import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import transforms
from torch.utils.data import DataLoader, Subset
import medmnist
from medmnist import INFO
import tenseal as ts
import boto3
import io

# Modelo Adaptado para Pneumonia (2 Classes)
class SimpleCNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(1, 8, 3), nn.ReLU(),
            nn.MaxPool2d(2),
        )
        self.fc = nn.Sequential(
            nn.Linear(8 * 13 * 13, 64), nn.ReLU(),
            nn.Linear(64, 2),
        )

    def forward(self, x):
        return self.fc(self.conv(x).view(x.size(0), -1))


# Configuração do Cliente (Hospitais)
CLIENT_ID = int(os.getenv("CLIENT_ID", "0"))
NUM_CLIENTS = int(os.getenv("NUM_CLIENTS", "3"))
SERVER_ADDRESS = os.getenv("SERVER_ADDRESS", "server:8080")
PARTITION_MODE = os.getenv("PARTITION_MODE", "iid").lower()
DIRICHLET_ALPHA = float(os.getenv("DIRICHLET_ALPHA", "0.5"))
SEED = 42

# ---- Configuração AWS ----
s3_client = boto3.client('s3', region_name='eu-west-1')
BUCKET_NAME = "fhe-cloud-chunks-90b21d10"

# Funções Auxiliares de Fatiamento (Chunking)
def get_model_shapes():
    return [p.shape for p in model.parameters()]

def flatten_weights(weights):
    # Espalma todas as matrizes para um único vetor 1D gigante
    return np.concatenate([w.flatten() for w in weights])

def unflatten_weights(flat_weights, shapes):
    # Reconstrói as camadas da rede neuronal a partir do vetor 1D
    weights = []
    idx = 0
    for shape in shapes:
        size = np.prod(shape)
        weights.append(flat_weights[idx : idx + size].reshape(shape))
        idx += size
    return weights

# Particionamento dos Dados (IID e Dirichlet)
def iid_partition(num_samples, num_clients, seed):
    rng = np.random.default_rng(seed)
    perm = rng.permutation(num_samples)
    return np.array_split(perm, num_clients)

def dirichlet_partition(targets, num_clients, alpha, seed):
    rng = np.random.default_rng(seed)
    targets = np.array(targets)
    num_classes = int(targets.max()) + 1
    client_idx = [[] for _ in range(num_clients)]

    for c in range(num_classes):
        idx_c = np.where(targets == c)[0]
        rng.shuffle(idx_c)
        proportions = rng.dirichlet([alpha] * num_clients)
        cuts = (np.cumsum(proportions) * len(idx_c)).astype(int)[:-1]
        for i, split in enumerate(np.split(idx_c, cuts)):
            client_idx[i].extend(split.tolist())

    return [np.array(ix) for ix in client_idx]


def get_loaders():
    # Setup para o MedMNIST
    data_flag = 'pneumoniamnist'
    info = INFO[data_flag]
    DataClass = getattr(medmnist, info['python_class'])

    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize(mean=[.5], std=[.5])
    ])

    trainset = DataClass(split='train', transform=transform, download=True, root="/data")
    testset = DataClass(split='test', transform=transform, download=True, root="/data")

    targets = trainset.labels.squeeze()

    if PARTITION_MODE == "dirichlet":
        partitions = dirichlet_partition(
            targets, NUM_CLIENTS, DIRICHLET_ALPHA, SEED
        )
    else:
        partitions = iid_partition(len(trainset), NUM_CLIENTS, SEED)

    my_indices = partitions[CLIENT_ID]
    subset = Subset(trainset, my_indices)

    # agora temos apenas as classes 0 (Normal) e 1 (Pneumonia)
    client_targets = targets[my_indices]
    class_counts = np.bincount(client_targets, minlength=2)
    print(
        f"[Hospital {CLIENT_ID}] Modo={PARTITION_MODE} "
        f"Alpha={DIRICHLET_ALPHA if PARTITION_MODE == 'dirichlet' else '-'} "
        f"Imagens Locais={len(subset)}",
        flush=True,
    )
    print(f"[Hospital {CLIENT_ID}] Distribuição (Normal / Pneumonia): {class_counts.tolist()}", flush=True)

    train_loader = DataLoader(subset, batch_size=32, shuffle=True)
    test_loader = DataLoader(testset, batch_size=128, shuffle=False)
    
    return train_loader, test_loader


trainloader, testloader = get_loaders()

# Garantir que todos os hospitais inicializam a rede com os exatos mesmos pesos!
torch.manual_seed(SEED)
model = SimpleCNN()
optimizer = optim.SGD(model.parameters(), lr=0.01)
criterion = nn.CrossEntropyLoss()

# Configuração e Chaves FHE
print("[Hospital] A carregar Contexto Privado FHE (com Secret Key)...", flush=True)
with open("/keys/secret_context.bytes", "rb") as f:
    # O cliente tem o contexto completo, incluindo a Secret Key para cifrar e decifrar.
    fhe_context = ts.context_from(f.read())

# O tamanho máximo de um vetor CKKS é metade do poly_modulus_degree
# Ver fhe_keys.py para a definição (8192 / 2 = 4096)
CHUNK_SIZE = 4096

# Cliente Flower (Agora com Cifragem Homomórfica) - Implementação do FedAvg
class HospitalClient(fl.client.NumPyClient):
    def __init__(self):
        self.round_counter = 0
    
    def get_parameters(self, config):
        current_round = config.get("server_round", self.round_counter)
        print(f"[Hospital {CLIENT_ID}] A cifrar e a enviar fatias para a AWS (Ronda {current_round})...", flush=True)
        
        weights = [p.detach().cpu().numpy() for p in model.parameters()]
        flat_weights = flatten_weights(weights)

        encrypted_chunks = []
        for i in range(0, len(flat_weights), CHUNK_SIZE):
            chunk = flat_weights[i : i + CHUNK_SIZE]
            enc_vector = ts.ckks_vector(fhe_context, chunk)
            enc_bytes = np.frombuffer(enc_vector.serialize(), dtype=np.uint8)
            
            # INÍCIO DO UPLOAD PARA S3 
            # Organizar por pastas na Cloud: ex: "Ronda_1/Hospital_1/chunk_0.bytes"
            s3_path = f"Ronda_{current_round}/Hospital_{CLIENT_ID}/chunk_{i//CHUNK_SIZE}.bytes"
            
            # O boto3 precisa que os bytes estejam num "ficheiro virtual" para fazer upload
            file_obj = io.BytesIO(enc_bytes)
            s3_client.upload_fileobj(file_obj, BUCKET_NAME, s3_path)
            # FIM DO UPLOAD PARA S3 

            encrypted_chunks.append(enc_bytes)

        print(f"[Hospital {CLIENT_ID}] {len(encrypted_chunks)} fatias enviadas para o S3 com sucesso!", flush=True)
        return encrypted_chunks

    def set_parameters(self, parameters):
        if not parameters:
            return

        print(f"[Hospital {CLIENT_ID}] A decifrar parâmetros recebidos do servidor...", flush=True)
        shapes = get_model_shapes()
        flat_weights = []

        for enc_chunk_np in parameters:
            # 1. Recuperar as bytes puras do array numpy
            enc_bytes = enc_chunk_np.tobytes()
            # 2. Reconstruir o vetor CKKS e Decifrar (usando a Secret Key local)
            enc_vector = ts.ckks_vector_from(fhe_context, enc_bytes)
            decrypted_chunk = enc_vector.decrypt()
            flat_weights.extend(decrypted_chunk)

        # 3. Reconstruir a estrutura original da CNN
        weights = unflatten_weights(np.array(flat_weights), shapes)

        # 4. Injetar na rede neuronal
        for p, new_p in zip(model.parameters(), weights):
            p.data = torch.tensor(new_p, dtype=p.dtype)

    def fit(self, parameters, config):
        self.round_counter = config.get("server_round", self.round_counter + 1)
        self.set_parameters(parameters)
        model.train()
        for images, labels in trainloader:
            labels = labels.squeeze(1).long()
            optimizer.zero_grad()
            loss = criterion(model(images), labels)
            loss.backward()
            optimizer.step()
        return self.get_parameters(config=config), len(trainloader.dataset), {}

    def evaluate(self, parameters, config):
        self.set_parameters(parameters)
        model.eval()
        loss, correct, total = 0.0, 0, 0
        with torch.no_grad():
            for images, labels in testloader:
                labels = labels.squeeze(1).long()
                output = model(images)
                # Multiply by batch size to get the true sum of losses
                loss += criterion(output, labels).item() * labels.size(0)
                correct += (output.argmax(1) == labels).sum().item()
                total += labels.size(0)
        average_loss = loss / total if total > 0 else 0.0
        return average_loss, total, {"accuracy": correct / total if total > 0 else 0.0}

fl.client.start_client(
    server_address=SERVER_ADDRESS,
    client=HospitalClient().to_client(),
)
