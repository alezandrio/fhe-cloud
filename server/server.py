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
        all_client_chunks = [fl.common.parameters_to_ndarrays(res.parameters) for _, res in results]
        
        num_clients = len(all_client_chunks)
        num_chunks = len(all_client_chunks[0])
        print(f"[Servidor] Recebidas {num_chunks} fatias de {num_clients} hospitais.")

        aggregated_chunks = []

        for chunk_idx in range(num_chunks):
            print(f"   ↳ A somar fatia {chunk_idx + 1}/{num_chunks}...", end="\r")
            
            first_client_bytes = all_client_chunks[0][chunk_idx].tobytes()
            sum_vector = ts.ckks_vector_from(public_context, first_client_bytes)

            for client_idx in range(1, num_clients):
                client_chunk_bytes = all_client_chunks[client_idx][chunk_idx].tobytes()
                next_vector = ts.ckks_vector_from(public_context, client_chunk_bytes)
                sum_vector += next_vector 
            
            avg_vector = sum_vector * (1 / num_clients)
            serialized_chunk = np.frombuffer(avg_vector.serialize(), dtype=np.uint8)
            aggregated_chunks.append(serialized_chunk)

        print(f"\n[Servidor] Agregação concluída para a Ronda {server_round}.")
        return fl.common.ndarrays_to_parameters(aggregated_chunks), {}

    def aggregate_evaluate(
        self,
        server_round: int,
        results: List[Tuple[fl.server.client_proxy.ClientProxy, fl.common.EvaluateRes]],
        failures: List[Union[Tuple[fl.server.client_proxy.ClientProxy, fl.common.EvaluateRes], BaseException]],
    ) -> Tuple[Optional[float], Dict[str, fl.common.Scalar]]:
        
        # 1. Chamar a função original do FedAvg para ele fazer as matemáticas (médias ponderadas)
        aggregated_loss, aggregated_metrics = super().aggregate_evaluate(server_round, results, failures)
        
        # 2. Imprimir o resultado no nosso terminal
        if aggregated_metrics and "global_accuracy" in aggregated_metrics:
            accuracy = aggregated_metrics["global_accuracy"] * 100
            print(f"[Ronda {server_round} - AVALIAÇÃO] Precisão Global: {accuracy:.2f}%")
        else:
            print(f"[Ronda {server_round}] Sem métricas de avaliação dos hospitais.")

        return aggregated_loss, aggregated_metrics

# Início do Servidor 
def evaluate_metrics_aggregation_fn(metrics: List[Tuple[int, Dict[str, float]]]) -> Dict[str, float]:
    if not metrics:
        return {}
    accuracies = [num_examples * m["accuracy"] for num_examples, m in metrics]
    examples = [num_examples for num_examples, _ in metrics]
    
    total_examples = sum(examples)
    if total_examples == 0:
        return {}
    return {"global_accuracy": sum(accuracies) / total_examples}

def fit_config(server_round: int) -> Dict[str, fl.common.Scalar]:
    return {"server_round": server_round}

# Definição da estratégia customizada
strategy = FHEFedAvg(
    fraction_fit=1.0,
    min_fit_clients=3,
    min_available_clients=3,
    evaluate_metrics_aggregation_fn=evaluate_metrics_aggregation_fn,
    on_fit_config_fn=fit_config,
)

print("[Servidor] Maestro Central FHE à espera dos hospitais na porta 8080...")
fl.server.start_server(
    server_address="0.0.0.0:8080",
    config=fl.server.ServerConfig(num_rounds=5),
    strategy=strategy,
)