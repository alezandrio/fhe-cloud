import boto3
import time
import csv
from datetime import datetime, timedelta

# Configurações do Projeto
LOG_GROUP_NAME = '/aws/lambda/fhe_chunk_aggregator'
REGION_NAME = 'eu-west-1'
HOURS_AGO = 4 # Extrair métricas das últimas 4 horas
CSV_FILENAME = 'lambda_metrics_fhe.csv'

def export_cloudwatch_metrics():
    print("A ligar à AWS CloudWatch Logs...")
    client = boto3.client('logs', region_name=REGION_NAME)

    # Definir a janela temporal
    end_time = int(datetime.now().timestamp())
    start_time = int((datetime.now() - timedelta(hours=HOURS_AGO)).timestamp())

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
    print(f"Query {query_id} iniciada. A aguardar processamento...")

    # Polling ativo até a AWS terminar a extração
    response = None
    while response == None or response['status'] == 'Running':
        time.sleep(2)
        response = client.get_query_results(queryId=query_id)

    if response['status'] != 'Complete':
        raise Exception(f"❌ Erro na extração: {response['status']}")

    results = response['results']
    print(f"Extração concluída. {len(results)} execuções encontradas.")

    # Exportar para CSV
    with open(CSV_FILENAME, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Timestamp', 'Request_ID', 'Init_Duration_ms', 'Duration_ms', 'Billed_Duration_ms', 'Max_Memory_MB'])

        for result in results:
            # Transformar a lista de dicionários da AWS num dicionário Python fácil de ler
            row_dict = {field['field']: field['value'] for field in result}
            
            # Tratamento de dados ausentes (Warm Starts não têm InitDuration) e conversão de bytes para MB
            init_dur = row_dict.get('@initDuration', '0')
            mem_mb = round(float(row_dict.get('@maxMemoryUsed', 0)) / 1000000, 2)
            
            writer.writerow([
                row_dict.get('@timestamp'),
                row_dict.get('@requestId'),
                init_dur,
                row_dict.get('@duration'),
                row_dict.get('@billedDuration'),
                mem_mb
            ])

    print(f"Ficheiro '{CSV_FILENAME}' gravado com sucesso. Pronto para análise estatística!")

if __name__ == "__main__":
    export_cloudwatch_metrics()
