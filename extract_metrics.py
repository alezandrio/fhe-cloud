import boto3
import time
import csv
from datetime import datetime, timedelta

# Configurações do Projeto
LOG_GROUP_NAME = '/aws/lambda/fhe_chunk_aggregator'
REGION_NAME = 'eu-west-1'
HOURS_AGO = 4 # Extrair métricas das últimas 4 horas
CSV_FILENAME = 'cloud_compute_metrics.csv' # Nome atualizado para a nova arquitetura

def export_cloudwatch_metrics():
    print("A ligar à AWS CloudWatch Logs...")
    client = boto3.client('logs', region_name=REGION_NAME)

    # Definir a janela temporal de extração
    end_time = int(datetime.now().timestamp())
    start_time = int((datetime.now() - timedelta(hours=HOURS_AGO)).timestamp())

    # A query extrai os dados crus diretamente da AWS
    query = """
    filter @type = "REPORT"
    | display @timestamp, @requestId, @initDuration, @duration, @billedDuration, @maxMemoryUsed
    | sort @timestamp asc
    """

    # Iniciar a query na AWS
    start_query_response = client.start_query(
        logGroupName=LOG_GROUP_NAME,
        startTime=start_time,
        endTime=end_time,
        queryString=query
    )
    query_id = start_query_response['queryId']
    print(f"Query {query_id} iniciada. A aguardar processamento da Cloud...")

    # Polling ativo até a AWS terminar a extração (espera 2 segundos entre tentativas)
    response = None
    while response == None or response['status'] == 'Running':
        time.sleep(2)
        response = client.get_query_results(queryId=query_id)

    if response['status'] != 'Complete':
        raise Exception(f"Erro na extração: {response['status']}")

    results = response['results']
    print(f"Extração concluída. {len(results)} invocações de Lambda encontradas.")

    # Exportar para CSV com a nova estrutura de dados
    with open(CSV_FILENAME, mode='w', newline='') as file:
        writer = csv.writer(file)
        # Cabeçalho atualizado com a classificação 'Type'
        writer.writerow(['Timestamp', 'Request_ID', 'Type', 'Init_Duration_ms', 'Duration_ms', 'Billed_Duration_ms', 'Max_Memory_MB'])

        for result in results:
            # Transformar a lista de dicionários da AWS num dicionário Python de fácil acesso
            row_dict = {field['field']: field['value'] for field in result}

            # Extrair os tempos cruciais
            init_dur = row_dict.get('@initDuration', '0')
            duration = row_dict.get('@duration', '0')
            billed_dur = row_dict.get('@billedDuration', '0')

            # LÓGICA DE DETEÇÃO DE COLD START
            # Se a AWS registou um Init_Duration > 0, foi um Cold Start. Caso contrário, foi Warm Start.
            invoke_type = 'Cold' if float(init_dur) > 0 else 'Warm'

            # Tratamento da memória: Converter os bytes puros da AWS para Megabytes (MB)
            mem_str = row_dict.get('@maxMemoryUsed', '0')
            mem_mb = round(float(mem_str) / 1000000, 2)

            writer.writerow([
                row_dict.get('@timestamp'),
                row_dict.get('@requestId'),
                invoke_type,     # Classificação gerada automaticamente
                init_dur,        # Penalização de arranque (se existir)
                duration,        # Tempo real de processamento homomórfico
                billed_dur,      # Tempo faturado pela AWS
                mem_mb           # Consumo máximo de RAM
            ])

    print(f"Ficheiro '{CSV_FILENAME}' gravado com sucesso. Pronto para a pipeline de análise!")

if __name__ == "__main__":
    export_cloudwatch_metrics()
