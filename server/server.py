import flwr as fl
from typing import List, Tuple, Dict

# Função de agregação de métricas para o Artigo
def weighted_average(metrics: List[Tuple[int, dict]]) -> dict:
    """
    Esta função recolhe a precisão (accuracy) de cada um dos 3 hospitais.
    Como o Hospital 1 tem 60% dos dados, ele tem de valer mais
    na média final do que o Hospital 3 (que só tem 10%).
    """
    # Multiplica a precisão de cada hospital pelo número de exemplos (imagens) que testou
    accuracies = [num_examples * m["accuracy"] for num_examples, m in metrics]
    examples = [num_examples for num_examples, _ in metrics]

    # Calcula a média global
    global_accuracy = sum(accuracies) / sum(examples)
    
    print(f"[Métrica Global] Precisão Média (Accuracy) da Ronda: {global_accuracy * 100:.2f}%")
    
    return {"global_accuracy": global_accuracy}

# Configuração da Estratégia
# Usamos o FedAvg (Média Federada) padrão para a Fase 1 (Plaintext).
# Na Fase 2 (FHE), vamos alterar isto para lidar com os Chunks Encriptados.
strategy = fl.server.strategy.FedAvg(
    fraction_fit=1.0,           # Treina em todos os clientes disponíveis
    fraction_evaluate=1.0,      # Avalia em todos os clientes disponíveis
    min_fit_clients=3,          # Exige os nossos 3 hospitais
    min_evaluate_clients=3,     
    min_available_clients=3,    
    evaluate_metrics_aggregation_fn=weighted_average, # gráficos
)

# Arranque do Servidor
print("A iniciar o Servidor Central de Federated Learning (FHE-Cloud)...")

# 5 rondas para dar tempo à rede neural (CNN) de aprender algo visível
fl.server.start_server(
    server_address="0.0.0.0:8080",
    config=fl.server.ServerConfig(num_rounds=5),
    strategy=strategy,
)