import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import os

# 1. Configurações Globais de Estilo (Padrão de Publicação Q1 - IEEE/Elsevier)
plt.rcParams.update({
    'font.size': 12,
    'font.family': 'serif',       # Fonte serifada ideal para artigos em LaTeX
    'axes.labelsize': 13,
    'axes.titlesize': 14,
    'legend.fontsize': 11,
    'xtick.labelsize': 11,
    'ytick.labelsize': 11,
    'figure.autolayout': True,
    'figure.dpi': 300             # Alta resolução garantida para submissão
})

CSV_FILE = 'client_ml_metrics.csv'

def generate_convergence_plot():
    print(f"A ler os dados de {CSV_FILE}...")
    
    if not os.path.exists(CSV_FILE):
        print(f"Ficheiro {CSV_FILE} não encontrado!")
        return

    # 2. Carregar e Tratar Dados do FHE (Do CSV)
    df = pd.read_csv(CSV_FILE)
    df['Hospital_ID'] = df['Hospital_ID'].str.replace('Hospital', 'Client')
    
    round_stats = df.groupby('Ronda').agg({
        'Global_Accuracy': 'mean',
        'Global_Loss': 'mean'
    }).reset_index()

    x_rounds = round_stats['Ronda']

    # 3. Dados do Baseline (Convertidos corretamente para a escala do gráfico)
    # Nota: A accuracy no outro script estava em %, aqui dividimos por 100 para alinhar com o eixo [0, 1]
    acc_baseline = [62.18 / 100, 75.64 / 100, 78.04 / 100, 85.42 / 100, 84.94 / 100]
    loss_baseline = [3.2133, 2.9542, 2.7822, 2.1892, 1.9941]

    # 4. Criar a Figura com Eixo Y Duplo
    fig, ax1 = plt.subplots(figsize=(8, 5.5))

    # --- EIXO 1 (Esquerdo): ACCURACY (Tons de Azul) ---
    color_acc = '#1f77b4'
    
    # Linha FHE-Cloud (Sua abordagem)
    line1_fhe, = ax1.plot(x_rounds, round_stats['Global_Accuracy'], color=color_acc, marker='o', 
                          linestyle='-', linewidth=2.2, markersize=7, label='FHE-Cloud (CKKS) - Accuracy')
    
    # Linha Baseline
    line1_base, = ax1.plot(x_rounds, acc_baseline, color=color_acc, marker='v', 
                           linestyle='--', linewidth=1.8, markersize=7, label='Baseline (Plaintext) - Accuracy')
    
    ax1.set_xlabel('Communication Round', fontweight='bold')
    ax1.set_ylabel('Accuracy', color=color_acc, fontweight='bold')
    ax1.tick_params(axis='y', labelcolor=color_acc)
    ax1.set_ylim([0.55, 1.0]) # Ajustado o limite inferior para dar zoom na zona de convergência
    ax1.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    ax1.yaxis.set_major_formatter(ticker.PercentFormatter(xmax=1.0)) # Transforma 0.85 em 85% no eixo de forma elegante
    ax1.grid(True, linestyle=':', alpha=0.6)

    # --- EIXO 2 (Direito): LOSS (Tons de Vermelho) ---
    ax2 = ax1.twinx()  
    color_loss = '#d62728'
    
    # Linha FHE-Cloud (Sua abordagem)
    line2_fhe, = ax2.plot(x_rounds, round_stats['Global_Loss'], color=color_loss, marker='s', 
                          linestyle='-', linewidth=2.2, markersize=7, label='FHE-Cloud (CKKS) - Loss')
    
    # Linha Baseline
    line2_base, = ax2.plot(x_rounds, loss_baseline, color=color_loss, marker='^', 
                           linestyle='--', linewidth=1.8, markersize=7, label='Baseline (Plaintext) - Loss')
    
    ax2.set_ylabel('Loss (Cross-Entropy)', color=color_loss, fontweight='bold')
    ax2.tick_params(axis='y', labelcolor=color_loss)
    
    # Escala dinâmica adaptada ao valor máximo absoluto das duas fontes de Loss
    max_loss_val = max(round_stats['Global_Loss'].max(), max(loss_baseline))
    ax2.set_ylim([0.0, max_loss_val * 1.1])
    ax2.grid(False) # Evita que as grelhas dos dois eixos colidam e criem linhas confusas

    # 5. Legenda e Título com Padrão Editorial
    # Agrupar todas as linhas para criar uma legenda única centralizada no topo
    lines = [line1_fhe, line1_base, line2_fhe, line2_base]
    labels = [l.get_label() for l in lines]
    
    # Organizado em 2 colunas para não estourar as margens
    ax1.legend(lines, labels, loc='upper center', bbox_to_anchor=(0.5, 1.18), 
               ncol=2, frameon=True, facecolor='white', edgecolor='none')

    # Título em inglês (obrigatório para Q1) e com margem segura ajustada pelo 'y'
    plt.title('Global Model Convergence: FHE-Cloud vs. Plaintext Baseline', y=1.20, fontweight='bold')

    # 6. Exportar em Alta Resolução Vetorial (PDF) e Rasterizada (PNG)
    pdf_filename = 'plot_convergence_scientific.pdf'
    png_filename = 'plot_convergence_scientific.png'
    tiff_filename = 'plot_convergence_scientific.tiff'
    
    plt.savefig(pdf_filename, format='pdf', bbox_inches='tight')
    plt.savefig(png_filename, format='png', dpi=300, bbox_inches='tight')
    plt.savefig(tiff_filename, format='tiff', dpi=300, bbox_inches='tight')
    
    print(f"Gráficos gerados com sucesso: '{pdf_filename}' e '{png_filename}'")
    plt.show()

if __name__ == "__main__":
    generate_convergence_plot()