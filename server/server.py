import flwr as fl
from typing import List, Tuple, Union, Optional, Dict
import numpy as np
import tenseal as ts
import os

# Configuração e Chaves FHE
print("[Servidor] A carregar Contexto Público FHE...", flush=True)
with open("/keys/public_context.bytes", "rb") as f:
    # O servidor só tem a Chave Pública e a Chave Relin. NÃO tem a Secret Key.
    public_context = ts.context_from(f.read())

# Estratégia de Agregação Homomórfica
class FHEFedAvg(fl.server.strategy.FedAvg):
    def aggregate_fit(
        self,
        server_round: int,
        results: List[Tuple[fl.server.client_proxy.ClientProxy, fl.common.FitRes]],
        failures: List[Union[Tuple[fl.server.client_proxy.ClientProxy, fl.common.FitRes], BaseException]],
    ) -> Tuple[Optional[fl.common.Parameters], Dict[str, fl.common.Scalar]]:

        if not results:
            return None, {}

        print(f"[Ronda {server_round}] A iniciar Agregação Homomórfica (MapReduce Style)...")

        # 1. Extrair os parâmetros de cada cliente
        # Cada cliente enviou uma lista de fatias (chunks) em bytes
        all_client_chunks = [fl.common.parameters_to_ndarrays(res.parameters) for _, res in results]
        
        # 2. Verificar consistência
        num_clients = len(all_client_chunks)
        num_chunks = len(all_client_chunks[0])
        print(f"[Servidor] Recebidas {num_chunks} fatias de {num_clients} hospitais.")

        # 3. Agregação Espacial (Soma Homomórfica das Fatias)
        # É aqui que o MapReduce na Cloud vai brilhar na Fase 4.
        aggregated_chunks = []

        for chunk_idx in range(num_chunks):
            print(f"   ↳ A somar fatia {chunk_idx + 1}/{num_chunks}...", end="\r")
            
            # Criar o contentor para a soma (começa com o primeiro cliente)
            first_client_bytes = all_client_chunks[0][chunk_idx].tobytes()
            sum_vector = ts.ckks_vector_from(public_context, first_client_bytes)

            # Somar os restantes clientes (Soma Homomórfica cega)
            for client_idx in range(1, num_clients):
                client_chunk_bytes = all_client_chunks[client_idx][chunk_idx].tobytes()
                next_vector = ts.ckks_vector_from(public_context, client_chunk_bytes)
                sum_vector += next_vector # A magia acontece aqui!
            
            # Média: Dividir pelo número de clientes (também de forma homomórfica)
            avg_vector = sum_vector * (1 / num_clients)
            
            # Converter de volta para bytes para devolver aos hospitais
            serialized_chunk = np.frombuffer(avg_vector.serialize(), dtype=np.uint8)
            aggregated_chunks.append(serialized_chunk)

        print(f"\n[Servidor] Agregação concluída para a Ronda {server_round}.")
        
        # Converter a lista de fatias para o formato que o Flower entende
        return fl.common.ndarrays_to_parameters(aggregated_chunks), {}

# Início do Servidor 
def evaluate_metrics_aggregation_fn(metrics: List[Tuple[int, Dict[str, float]]]) -> Dict[str, float]:
    accuracies = [num_examples * m["accuracy"] for num_examples, m in metrics]
    examples = [num_examples for num_examples, _ in metrics]
    return {"global_accuracy": sum(accuracies) / sum(examples)}

# Definição da estratégia customizada
strategy = FHEFedAvg(
    fraction_fit=1.0,
    min_fit_clients=3,
    min_available_clients=3,
    evaluate_metrics_aggregation_fn=evaluate_metrics_aggregation_fn,
)

print("[Servidor] Maestro Central FHE à espera dos hospitais na porta 8080...")
fl.server.start_server(
    server_address="0.0.0.0:8080",
    config=fl.server.ServerConfig(num_rounds=5),
    strategy=strategy,
)