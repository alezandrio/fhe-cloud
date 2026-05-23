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
import time
import botocore

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
BUCKET_NAME = os.getenv("BUCKET_NAME")
if not BUCKET_NAME:
    raise ValueError("A variável BUCKET_NAME não foi definida. Verifique o output do Terraform e injete-a no contentor.")

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

        chunks_uploaded = 0
        for i in range(0, len(flat_weights), CHUNK_SIZE):
            chunk = flat_weights[i : i + CHUNK_SIZE]
            enc_vector = ts.ckks_vector(fhe_context, chunk)
            # Passamos as bytes geradas diretamente (sem numpy intermediário)
            enc_bytes = enc_vector.serialize()
            
            s3_path = f"incoming/Ronda_{current_round}/Hospital_{CLIENT_ID}/chunk_{i//CHUNK_SIZE}.bytes"
            
            file_obj = io.BytesIO(enc_bytes)
            s3_client.upload_fileobj(file_obj, BUCKET_NAME, s3_path)
            chunks_uploaded += 1

        print(f"[Hospital {CLIENT_ID}] {chunks_uploaded} fatias enviadas para o S3 com sucesso!", flush=True)
        
        # CORREÇÃO P1: Em vez de enviar as fatias pesadas de volta pelo Flower,
        # enviamos apenas um "sinal" (flag) a indicar que o upload terminou.
        dummy_signal = [np.array([1], dtype=np.float32)]
        return dummy_signal

    def set_parameters(self, parameters):
        # Como delegamos tudo para a AWS S3, vamos IGNORAR o dummy signal do Flower gRPC
        pass

    def download_and_decrypt_global_model(self, round_to_download):
        # Se for a ronda 0 (antes da 1ª ronda de treino), não há modelo global para transferir.
        if round_to_download == 0:
            return
            
        print(f"[Hospital {CLIENT_ID}] A transferir e decifrar modelo agregado da AWS (Ronda {round_to_download})...", flush=True)
        shapes = get_model_shapes()
        flat_weights = []
        
        dummy_weights = [p.detach().cpu().numpy() for p in model.parameters()]
        total_elements = len(flatten_weights(dummy_weights))
        num_chunks = (total_elements + CHUNK_SIZE - 1) // CHUNK_SIZE

        for i in range(num_chunks):
            s3_path = f"outgoing/Ronda_{round_to_download}/chunk_{i}_aggregated.bytes"
            
            # Barreira de Polling: O Cliente espera bloqueado até a AWS Lambda acabar de processar!
            while True:
                try:
                    obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=s3_path)
                    enc_bytes = obj['Body'].read()
                    break
                except botocore.exceptions.ClientError as e:
                    if e.response['Error']['Code'] in ['NoSuchKey', '404']:
                        print(f"[Hospital {CLIENT_ID}] ⏳ AWS Lambda a processar. A aguardar {s3_path}...", flush=True)
                        time.sleep(5)
                    else:
                        raise e
            
            # Reconstruir e Decifrar
            enc_vector = ts.ckks_vector_from(fhe_context, enc_bytes)
            decrypted_chunk = enc_vector.decrypt()
            flat_weights.extend(decrypted_chunk)
            
        # Reconstruir a estrutura original da CNN
        weights = unflatten_weights(np.array(flat_weights), shapes)

        for p, new_p in zip(model.parameters(), weights):
            p.data = torch.tensor(new_p, dtype=p.dtype)

    def fit(self, parameters, config):
        self.round_counter = config.get("server_round", self.round_counter + 1)
        # Transferimos do S3 o modelo final da ronda anterior ANTES de iniciar um novo treino local
        self.download_and_decrypt_global_model(self.round_counter - 1)
        model.train()
        for images, labels in trainloader:
            labels = labels.squeeze(1).long()
            optimizer.zero_grad()
            loss = criterion(model(images), labels)
            loss.backward()
            optimizer.step()
        return self.get_parameters(config=config), len(trainloader.dataset), {}

    def evaluate(self, parameters, config):
        current_round = config.get("server_round", self.round_counter)
        # Na fase de avaliação, queremos testar o modelo agregado DESTA ronda que acabou de ser processado
        self.download_and_decrypt_global_model(current_round)
        model.eval()
        loss, correct, total = 0.0, 0, 0
        with torch.no_grad():
            for images, labels in testloader:
                labels = labels.squeeze(1).long()
                output = model(images)
                # Multiplicamos a loss pelo número de exemplos para depois calcular a média ponderada globalmente no servidor
                loss += criterion(output, labels).item() * labels.size(0)
                correct += (output.argmax(1) == labels).sum().item()
                total += labels.size(0)
        average_loss = loss / total if total > 0 else 0.0
        return average_loss, total, {"accuracy": correct / total if total > 0 else 0.0}

fl.client.start_client(
    server_address=SERVER_ADDRESS,
    client=HospitalClient().to_client(),
)
