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

        # O servidor agora apenas atua como Orquestrador de Fluxo
        print(f"\n[Ronda {server_round}] 📡 Recebida confirmação de {len(results)} hospitais!")
        print(f"[Servidor] Sucesso! Os clientes terminaram o upload dos chunks cifrados para o S3.")
        print(f"[Servidor] A matemática pesada de agregação FHE foi totalmente delegada para a AWS.")
        
        # Como a agregação real vai acontecer de forma assíncrona/serverless no S3 via Lambdas,
        # o servidor Flower não precisa de processar tensores homomórficos locais nesta fase.
        # Devolvemos um parâmetro leve e fictício ("dummy") apenas para cumprir a assinatura do Flower
        # e permitir que o ciclo de treino avance para a próxima ronda.
        dummy_signal = [np.array([0.0], dtype=np.float32)]
        
        return fl.common.ndarrays_to_parameters(dummy_signal), {}

    def aggregate_evaluate(
        self,
        server_round: int,
        results: List[Tuple[fl.server.client_proxy.ClientProxy, fl.common.EvaluateRes]],
        failures: List[Union[Tuple[fl.server.client_proxy.ClientProxy, fl.common.EvaluateRes], BaseException]],
    ) -> Tuple[Optional[float], Dict[str, fl.common.Scalar]]:
        
        # Mantemos esta função intacta! Os hospitais continuam a avaliar o modelo localmente
        # e a enviar métricas limpas (não cifradas, ex: loss e acerto) de volta ao servidor via gRPC.
        aggregated_loss, aggregated_metrics = super().aggregate_evaluate(server_round, results, failures)
        
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