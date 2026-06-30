import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import seaborn as sns
import os

# 1. Configurações Globais de Estilo (Artigo Científico)
plt.rcParams.update({
    'font.size': 12,
    'font.family': 'sans-serif',
    'axes.labelsize': 14,
    'axes.titlesize': 14,
    'xtick.labelsize': 12,
    'ytick.labelsize': 12,
    'figure.autolayout': True
})

# Paleta de cores semântica (Azul para Edge, Laranja para Cloud)
COLORS = {
    'Local Encryption (Edge)': '#1f77b4',
    'Cloud Aggregation (AWS)': '#ff7f0e',
    'Local Decryption (Edge)': '#2ca02c'
}

def generate_latency_boxplot():
    client_csv = 'client_ml_metrics.csv'
    cloud_csv = 'cloud_compute_metrics.csv'
    
    print("A ler e a cruzar dados de Edge e Cloud...")
    
    if not os.path.exists(client_csv) or not os.path.exists(cloud_csv):
        print(f"Erro: Faltam ficheiros CSV. Garante que tens o {client_csv} e o {cloud_csv}.")
        return

    # 2. Extração e Limpeza de Dados
    df_client = pd.read_csv(client_csv)
    df_cloud = pd.read_csv(cloud_csv)
    
    dados_combinados = []
    
    # 1. Tempos de Encriptação Local
    for tempo in df_client['Encrypt_Time_ms'].dropna():
        dados_combinados.append({'Phase': 'Local Encryption (Edge)', 'Time (s)': float(tempo) / 1000.0})
        
    # 2. Tempos de Agregação na Cloud (COM FILTRO DE SANIDADE)
    # Ignorar as Lambdas "fantasma" que demoram apenas 2-10ms a verificar o S3
    for tempo in df_cloud['Duration_ms'].dropna():
        t_ms = float(tempo)
        # Só consideramos que houve processamento matemático se a Lambda correu mais de 100ms
        if t_ms > 100.0: 
            dados_combinados.append({'Phase': 'Cloud Aggregation (AWS)', 'Time (s)': t_ms / 1000.0})
        
    # 3. Tempos de Decifragem Local
    for tempo in df_client['Decrypt_Time_ms'].dropna():
        dados_combinados.append({'Phase': 'Local Decryption (Edge)', 'Time (s)': float(tempo) / 1000.0})
        
    df_plot = pd.DataFrame(dados_combinados)

    # 3. Criação da Figura (Boxplot)
    fig, ax = plt.subplots(figsize=(8, 6))
    
    # Desenhar o Boxplot usando Seaborn para um visual profissional
    sns.boxplot(x='Phase', y='Time (s)', hue='Phase', data=df_plot, ax=ax, 
                palette=COLORS, width=0.5, linewidth=1.5, legend=False,
                flierprops={"marker": "x", "color": "black", "alpha": 0.5}) # Outliers marcados com 'x'

    # 4. Magia Matemática: Escala Logarítmica
    ax.set_yscale('log')
    
    # Formatar o Eixo Y para mostrar números reais (ex: 0.1, 1, 10) em vez de notação científica (10^1)
    formatter = ticker.FuncFormatter(lambda y, _: '{:g}'.format(y))
    ax.yaxis.set_major_formatter(formatter)
    
    # Adicionar linhas de grelha subtis
    ax.yaxis.grid(True, linestyle='--', alpha=0.7, which='both')
    ax.xaxis.grid(False)

    # Ajustes de texto
    ax.set_xlabel('Computational Phase', fontweight='bold', labelpad=15)
    ax.set_ylabel('Execution Time (seconds) - Log Scale', fontweight='bold', labelpad=15)
    plt.title('Distribution of Computational Latency by Phase', pad=20, fontweight='bold')

    # 5. Exportação em Alta Resolução
    pdf_filename = 'plot_latency.pdf'
    png_filename = 'plot_latency.png'
    
    plt.savefig(pdf_filename, format='pdf', bbox_inches='tight')
    plt.savefig(png_filename, format='png', dpi=300, bbox_inches='tight')
    
    print(f"Boxplot gerado com sucesso: '{pdf_filename}' e '{png_filename}'")

if __name__ == "__main__":
    generate_latency_boxplot()