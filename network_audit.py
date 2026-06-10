import boto3
import csv
from datetime import datetime

# Configurações FinOps
BUCKET_NAME = 'fhe-cloud-chunks-9b9858ee' # Ex: fhe-cloud-chunks-abcd123
REGION = 'eu-west-1'
NUM_HOSPITAIS = 3
CSV_FILENAME = 'network_audit_results.csv'

def calcular_auditoria_rede():
    print(f"📊 A iniciar Auditoria de Tráfego de Rede no bucket: {BUCKET_NAME}...")
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

        # Conversões Científicas (MB)
        mb_incoming = bytes_incoming / (1024 * 1024)
        mb_outgoing_armazenado = bytes_outgoing / (1024 * 1024)
        
        # Cálculo de Egress (Tráfego de Saída Real gerado pela Cloud)
        # O ficheiro agregado é descarregado N vezes (1 vez por cada hospital)
        mb_egress_total = mb_outgoing_armazenado * NUM_HOSPITAIS
        mb_armazenamento_total = mb_incoming + mb_outgoing_armazenado

        # 1. Imprimir no Terminal
        print("\n=== RESULTADOS DA AUDITORIA FHE-CLOUD ===")
        print(f"📈 Ficheiros Uploaded (Incoming): {ficheiros_incoming}")
        print(f"📉 Ficheiros Agregados (Outgoing): {ficheiros_outgoing}")
        print("-" * 40)
        print(f"📥 Tráfego EDGE -> CLOUD (Data Ingress): {mb_incoming:.2f} MB ({mb_incoming/1024:.4f} GB)")
        print(f"📤 Tráfego CLOUD -> EDGE (Data Egress) : {mb_egress_total:.2f} MB ({mb_egress_total/1024:.4f} GB)")
        print(f"💽 Armazenamento Estático no S3        : {mb_armazenamento_total:.2f} MB")
        print("=========================================\n")

        # 2. Guardar em CSV (Rigor Científico)
        timestamp_agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(CSV_FILENAME, mode='a', newline='') as file:
            writer = csv.writer(file)
            
            # Se o ficheiro estiver vazio, escreve o cabeçalho primeiro
            if file.tell() == 0:
                writer.writerow(['Timestamp', 'Num_Hospitais', 'Ficheiros_In', 'Ficheiros_Out', 'Ingress_MB', 'Egress_MB', 'Storage_Total_MB'])
            
            writer.writerow([
                timestamp_agora,
                NUM_HOSPITAIS,
                ficheiros_incoming,
                ficheiros_outgoing,
                round(mb_incoming, 2),
                round(mb_egress_total, 2),
                round(mb_armazenamento_total, 2)
            ])
            
        print(f"💾 Sucesso! Dados da auditoria guardados no ficheiro: '{CSV_FILENAME}'")

    except Exception as e:
        print(f"❌ Erro ao aceder ao S3: {str(e)}")

if __name__ == "__main__":
    calcular_auditoria_rede()