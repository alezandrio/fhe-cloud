import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import os

# 1. Configurações Globais de Estilo
plt.rcParams.update({
    'font.size': 12,
    'font.family': 'sans-serif',
    'axes.labelsize': 13,
    'axes.titlesize': 14,
    'legend.fontsize': 11,
    'xtick.labelsize': 11,
    'ytick.labelsize': 11,
})

def generate_finops_plot():
    net_csv = 'network_finops_metrics.csv'
    cloud_csv = 'cloud_compute_metrics.csv'
    
    print("A ler dados de Rede e Cloud...")
    if not os.path.exists(net_csv) or not os.path.exists(cloud_csv):
        print("Erro: Faltam ficheiros CSV.")
        return

    # 2. Extração Dinâmica de Colunas
    df_net = pd.read_csv(net_csv)
    df_cloud = pd.read_csv(cloud_csv)

    col_ingress = [c for c in df_net.columns if 'Ingress' in c][0]
    col_egress = [c for c in df_net.columns if 'Egress' in c][0]
    col_ronda = [c for c in df_net.columns if 'Ronda' in c or 'Round' in c][0]
    col_ram = [c for c in df_cloud.columns if 'Memory' in c or 'RAM' in c][0]

    for col in [col_ingress, col_egress]:
        if df_net[col].dtype == object:
            df_net[col] = df_net[col].astype(str).str.extract(r'([\d\.]+)').astype(float)
            
    if df_cloud[col_ram].dtype == object:
        df_cloud[col_ram] = df_cloud[col_ram].astype(str).str.extract(r'([\d\.]+)').astype(float)

    df_net_grouped = df_net.groupby(col_ronda).mean(numeric_only=True).reset_index()
    avg_ram = df_cloud[col_ram].mean()

    # Lógica de Alinhamento Científico de Escalas
    # Como ambas as métricas partilham a grandeza (MB), unificamos os limites do eixo Y.
    max_payload = (df_net_grouped[col_ingress] + df_net_grouped[col_egress]).max()
    global_max = max(max_payload, avg_ram)
    
    # Arredondar para o próximo múltiplo de 50 para criar um limite superior limpo
    y_max_limit = np.ceil(global_max / 50) * 50 + 50 

    # 3. Criar a Figura com Eixo Y Duplo
    # Ligeiramente mais largo para dar espaço às labels do eixo Y sem espremer o gráfico
    fig, ax1 = plt.subplots(figsize=(10, 5.5)) 
    x = df_net_grouped[col_ronda]
    width = 0.55 

    # --- Plot 1: Eixo Esquerdo ---
    color_ingress = '#1f77b4' 
    color_egress = '#ff7f0e'  
    
    bar1 = ax1.bar(x, df_net_grouped[col_ingress], width, 
                   label='Network Ingress (Up)', color=color_ingress, edgecolor='black', linewidth=0.7)
    bar2 = ax1.bar(x, df_net_grouped[col_egress], width, 
                   bottom=df_net_grouped[col_ingress], 
                   label='Network Egress (Down)', color=color_egress, edgecolor='black', linewidth=0.7)

    ax1.set_xlabel('Federated Learning Round', fontweight='bold')
    ax1.set_ylabel('Network Payload (MB)', fontweight='bold', color='black')
    ax1.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    ax1.grid(True, axis='y', linestyle='--', alpha=0.4)
    ax1.set_ylim([0, y_max_limit]) # Aplicar limite unificado

    # --- Plot 2: Eixo Direito ---
    ax2 = ax1.twinx()
    color_ram = '#d62728' 
    
    line1, = ax2.plot(x, [avg_ram] * len(x), color=color_ram, marker='D', 
                      linestyle='-', linewidth=2.5, markersize=7, label='Lambda RAM Usage')
    
    ax2.set_ylabel('Peak Memory Consumption (MB)', color=color_ram, fontweight='bold')
    ax2.tick_params(axis='y', labelcolor=color_ram)
    ax2.set_ylim([0, y_max_limit]) # Aplicar o MESMO limite unificado

    # Anotação com "Caixa de Fundo" (Bbox) para evitar colisão visual
    ax2.annotate(f"{avg_ram:.1f} MB (Stable)", 
                 (x.iloc[len(x)//2], avg_ram), 
                 textcoords="offset points", 
                 xytext=(0, 15), # Ligeiramente mais acima
                 ha='center', 
                 fontsize=11, 
                 color=color_ram,
                 fontweight='bold',
                 bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="none", alpha=0.85))

    # 4. Legenda e Título
    bars_lines = [bar1, bar2, line1]
    labels = [l.get_label() for l in bars_lines]
    
    # Legenda em linha (ncol=3) e mais próxima do gráfico
    ax1.legend(bars_lines, labels, loc='lower center', bbox_to_anchor=(0.5, 1.02), 
               ncol=3, frameon=False)

    # Título com margem estruturada (pad) em vez de coordenada y forçada
    plt.title('Determinism of Network FinOps & Cloud Memory Scalability', 
              fontweight='bold', pad=45)

    # 5. Exportar
    # Ajustar as margens automaticamente de forma rigorosa antes de guardar
    fig.tight_layout() 
    
    plt.savefig('plot_finops.pdf', format='pdf', bbox_inches='tight')
    plt.savefig('plot_finops.png', format='png', dpi=300, bbox_inches='tight')
    print("Gráficos gerados com sucesso e com qualidade científica!")

if __name__ == "__main__":
    generate_finops_plot()