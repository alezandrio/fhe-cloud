import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import os

# 1. Configurações Globais de Estilo
plt.rcParams.update({
    'font.size': 12,
    'font.family': 'sans-serif',
    'axes.labelsize': 14,
    'axes.titlesize': 14,
    'legend.fontsize': 12,
    'xtick.labelsize': 12,
    'ytick.labelsize': 12,
    'figure.autolayout': True
})

CSV_FILE = 'client_ml_metrics.csv'

def generate_convergence_plot():
    print(f"A ler os dados de {CSV_FILE}...")
    
    if not os.path.exists(CSV_FILE):
        print(f"Ficheiro {CSV_FILE} não encontrado!")
        return

    # 2. Carregar e Tratar Dados
    df = pd.read_csv(CSV_FILE)
    df['Hospital_ID'] = df['Hospital_ID'].str.replace('Hospital', 'Client')
    
    round_stats = df.groupby('Ronda').agg({
        'Global_Accuracy': 'mean',
        'Global_Loss': 'mean'
    }).reset_index()

    # 3. Criar a Figura com Eixo Y Duplo
    fig, ax1 = plt.subplots(figsize=(8, 5))
    x_rounds = round_stats['Ronda']

    # --- Plot 1: Global Accuracy (Azul, Valores Acima, Percentagem) ---
    color1 = '#1f77b4'
    line1, = ax1.plot(x_rounds, round_stats['Global_Accuracy'], color=color1, marker='o', 
                      linestyle='-', linewidth=2, markersize=8, label='Global Accuracy')
    
    ax1.set_xlabel('Federated Learning Round', fontweight='bold')
    ax1.set_ylabel('Accuracy', color=color1, fontweight='bold')
    ax1.tick_params(axis='y', labelcolor=color1)
    ax1.set_ylim([0.0, 1.05]) # Limite 0 a 100%
    ax1.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    ax1.grid(True, linestyle='--', alpha=0.6)

    # Inserir o texto da percentagem em cada ponto
    for i, acc in enumerate(round_stats['Global_Accuracy']):
        ronda = x_rounds.iloc[i]
        y_offset = 7 if ronda == 2 else 12
        
        ax1.annotate(f"{acc*100:.2f}%", 
                     (ronda, acc), 
                     textcoords="offset points", 
                     xytext=(0, y_offset), 
                     ha='center', 
                     fontsize=10, 
                     color=color1,
                     fontweight='bold')

    # --- Plot 2: Global Loss (Vermelho, Valores Abaixo, Decimal) ---
    ax2 = ax1.twinx()  
    color2 = '#d62728'
    line2, = ax2.plot(x_rounds, round_stats['Global_Loss'], color=color2, marker='s', 
                      linestyle='--', linewidth=2, markersize=8, label='Global Loss')
    
    ax2.set_ylabel('Loss', color=color2, fontweight='bold')
    ax2.tick_params(axis='y', labelcolor=color2)
    
    # Limite aumentado (x 1.3) para dar espaço para o texto respirar
    max_loss = round_stats['Global_Loss'].max()
    ax2.set_ylim([0.0, max_loss * 1.3])

    # Inserir o texto decimal da Loss em cada ponto
    for i, loss in enumerate(round_stats['Global_Loss']):
        ronda = x_rounds.iloc[i]
        
        if ronda in [1, 2]:
            y_offset = 12  # Para cima do ponto
        else:
            y_offset = -18

        ax2.annotate(f"{loss:.4f}", 
                     (ronda, loss), 
                     textcoords="offset points", 
                     xytext=(0, y_offset), 
                     ha='center', 
                     fontsize=10, 
                     color=color2,
                     fontweight='bold')

    # 4. Legenda e Título Organizados
    # Mover a legenda para fora do gráfico (no topo)
    lines = [line1, line2]
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc='upper center', bbox_to_anchor=(0.5, 1.15), 
               ncol=2, frameon=False)

    # Subir o título para não colidir com a legenda
    plt.title('Convergence of Model Training over Homomorphic Encryption', y=1.2)

    # 5. Exportar em Alta Resolução
    pdf_filename = 'plot_convergence.pdf'
    png_filename = 'plot_convergence.png'
    
    plt.savefig(pdf_filename, format='pdf', bbox_inches='tight')
    plt.savefig(png_filename, format='png', dpi=300, bbox_inches='tight')
    
    print(f"Gráficos gerados com sucesso: '{pdf_filename}' e '{png_filename}'")

if __name__ == "__main__":
    generate_convergence_plot()