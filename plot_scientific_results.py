import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Configuração de estilo de publicação científica (MDPI / IEEE)
sns.set_theme(style="whitegrid", context="paper", font_scale=1.2)
plt.rcParams['font.family'] = 'serif'
plt.rcParams['figure.dpi'] = 300

def plot_federated_learning_metrics():
    # Rondas do modelo (1 a 5)
    rondas = np.arange(1, 6)
    
    # Accuracy (%)
    # === DADOS DO BASELINE (Texto Limpo / Sem Cifra) ===
    acc_baseline = [62.18, 75.64, 78.04, 85.42, 84.94]
    loss_baseline = [3.2133, 2.9542, 2.7822, 2.1892, 1.9941]

    # === DADOS REAIS FHE-CLOUD (Cifrado / MapReduce) ===
    acc_fhe = [62.50, 62.66, 71.63, 84.29, 84.13] 
    loss_fhe = [0.6314, 0.5733, 0.5029, 0.4330, 0.4063]
    
    # Criação da Figura com 2 Subplots (Lado a Lado)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    # Cores padronizadas para publicações científicas
    color_baseline = '#1f77b4' # Azul Mudo
    color_fhe = '#d62728'      # Vermelho Tijolo
    
    # --- GRÁFICO 1: GLOBAL ACCURACY ---
    ax1.plot(rondas, acc_baseline, marker='o', markersize=8, linewidth=2.5, 
             linestyle='--', color=color_baseline, label='Baseline (Plaintext)')
    ax1.plot(rondas, acc_fhe, marker='s', markersize=8, linewidth=2.5, 
             linestyle='-', color=color_fhe, label='FHE-Cloud (CKKS)')
    
    ax1.set_title('Convergência da Precisão Global (Accuracy)', fontweight='bold')
    ax1.set_xlabel('Ronda de Comunicação')
    ax1.set_ylabel('Accuracy (%)')
    ax1.set_xticks(rondas)
    ax1.set_ylim([60, 95])
    ax1.legend(loc='lower right', frameon=True, shadow=True)
    
    # --- GRÁFICO 2: GLOBAL LOSS ---
    ax2.plot(rondas, loss_baseline, marker='o', markersize=8, linewidth=2.5, 
             linestyle='--', color=color_baseline, label='Baseline (Plaintext)')
    ax2.plot(rondas, loss_fhe, marker='s', markersize=8, linewidth=2.5, 
             linestyle='-', color=color_fhe, label='FHE-Cloud (CKKS)')
    
    ax2.set_title('Evolução da Perda de Treino (Global Loss)', fontweight='bold')
    ax2.set_xlabel('Ronda de Comunicação')
    ax2.set_ylabel('Loss (Cross-Entropy)')
    ax2.set_xticks(rondas)
    ax2.set_ylim([0.2, 3.3])
    ax2.legend(loc='upper right', frameon=True, shadow=True)
    
    # Ajuste e Gravação em PDF/PNG para LaTeX
    plt.tight_layout()
    plt.savefig('scientific_evaluation_fhe_cloud.pdf', format='pdf', bbox_inches='tight')
    plt.savefig('scientific_evaluation_fhe_cloud.png', format='png', bbox_inches='tight', dpi=300)
    print("Gráficos gerados com sucesso e prontos a publicar!")
    plt.show()

if __name__ == "__main__":
    plot_federated_learning_metrics()