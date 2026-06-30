import boto3
import csv
import os
from datetime import datetime

# Configurações FinOps e Projeto
BUCKET_NAME = 'fhe-cloud-chunks-1ed27e93'
REGION = 'eu-west-1'
NUM_HOSPITAIS = 3
CSV_FILENAME = 'network_finops_metrics.csv' 

def calcular_auditoria_rede():
    print(f"A iniciar Auditoria de Tráfego de Rede no bucket: {BUCKET_NAME}...")
    s3_client = boto3.client('s3', region_name=REGION)
    paginator = s3_client.get_paginator('list_objects_v2')

    bytes_incoming = 0
    bytes_outgoing = 0
    ficheiros_incoming = 0
    ficheiros_outgoing = 0

    try:
        # Usar paginator para lidar com baldes com muitos ficheiros (>1000)
        for page in paginator.paginate(Bucket=BUCKET_NAME):
            if 'Contents' in page:
                for obj in page['Contents']:
                    key = obj['Key']
                    tamanho_bytes = obj['Size']
                    
                    if key.startswith('incoming/'):
                        bytes_incoming += tamanho_bytes
                        ficheiros_incoming += 1
                    elif key.startswith('outgoing/') and key.endswith('_aggregated.bytes'):
                        bytes_outgoing += tamanho_bytes
                        ficheiros_outgoing += 1

        # Conversões Científicas (para Megabytes)
        mb_incoming = bytes_incoming / (1024 * 1024)
        mb_outgoing_armazenado = bytes_outgoing / (1024 * 1024)
        
        # Cálculo de Egress (Tráfego de Saída Real gerado pela Cloud)
        # O ficheiro agregado é descarregado N vezes (1 vez por cada hospital)
        mb_egress_total = mb_outgoing_armazenado * NUM_HOSPITAIS
        
        # Armazenamento total ocupado no S3
        mb_armazenamento_total = mb_incoming + mb_outgoing_armazenado

        # Lógica Automática da Ronda
        ronda_atual = 1
        ficheiro_existe = os.path.isfile(CSV_FILENAME)
        
        if ficheiro_existe:
            # Conta as linhas existentes para inferir a ronda atual (exclui o cabeçalho)
            with open(CSV_FILENAME, 'r') as file:
                ronda_atual = sum(1 for row in file) # Se tem 1 linha (cabeçalho), ronda_atual = 1

        # Guardar em CSV (Rigor Científico)
        timestamp_agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(CSV_FILENAME, mode='a', newline='') as file:
            writer = csv.writer(file)
            
            # Se o ficheiro é novo, escreve o cabeçalho primeiro
            if not ficheiro_existe:
                writer.writerow(['Timestamp', 'Ronda', 'Ficheiros_In', 'Ficheiros_Out', 'Ingress_MB', 'Egress_MB', 'Storage_Total_MB'])
            
            # Escreve a linha de métricas da ronda atual
            writer.writerow([
                timestamp_agora,
                ronda_atual,
                ficheiros_incoming,
                ficheiros_outgoing,
                round(mb_incoming, 2),
                round(mb_egress_total, 2),
                round(mb_armazenamento_total, 2)
            ])
            
        print("\n=== RESULTADOS DA AUDITORIA (RONDA {}) ===".format(ronda_atual))
        print(f"Tráfego EDGE -> CLOUD (Ingress): {mb_incoming:.2f} MB")
        print(f"Tráfego CLOUD -> EDGE (Egress) : {mb_egress_total:.2f} MB")
        print(f"Armazenamento Estático no S3   : {mb_armazenamento_total:.2f} MB")
        print(f"Dados guardados com sucesso no ficheiro: '{CSV_FILENAME}'")

    except Exception as e:
        print(f"Erro ao aceder ao S3: {str(e)}")

if __name__ == "__main__":
    calcular_auditoria_rede()