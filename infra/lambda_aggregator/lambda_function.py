import json
import urllib.parse
import boto3
import numpy as np
import tenseal as ts
import botocore

s3_client = boto3.client('s3')
TOTAL_HOSPITALS = 3

def lambda_handler(event, context):
    # O S3 pode agrupar vários eventos (uploads simultâneos) numa só chamada à Lambda!
    # Temos de iterar sobre todos eles para não perder ficheiros.
    for record in event.get('Records', []):
        bucket = record['s3']['bucket']['name']
        key = urllib.parse.unquote_plus(record['s3']['object']['key'], encoding='utf-8')
        
        parts = key.split('/')
        if len(parts) != 4 or parts[0] != 'incoming':
            print(f"⏭Ficheiro {key} ignorado (fora da pasta incoming).")
            continue
            
        ronda = parts[1]
        chunk_file = parts[3] # Ex: "chunk_0.bytes"
        chunk_name = chunk_file.replace('.bytes', '') # Extrai apenas "chunk_0"
        
        # Definição das chaves para Controlo de Estado
        lock_key = f"locks/{ronda}/{chunk_name}.lock"
        aggregated_key = f"outgoing/{ronda}/{chunk_name}_aggregated.bytes"
        
        # PROTEÇÃO CONTRA RACE CONDITIONS (Verificação Dupla S3)
        try:
            # 1. Verifica se o resultado final já foi processado
            s3_client.head_object(Bucket=bucket, Key=aggregated_key)
            print(f"Ficheiro {chunk_name} já foi agregado. A abortar execução duplicada.")
            continue
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] != '404':
                raise e
                
        try:
            # 2. Verifica se existe um lock ativo
            s3_client.head_object(Bucket=bucket, Key=lock_key)
            print(f"Lock detetado para {chunk_name}. Outra Lambda está encarregue disto. A abortar.")
            continue
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] != '404':
                raise e

        # 1. BARREIRA DE SINCRONIZAÇÃO
        prefix = f"incoming/{ronda}/"
        response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
        
        ficheiros_deste_chunk = [
            obj['Key'] for obj in response.get('Contents', []) 
            if obj['Key'].endswith(chunk_file)
        ]
        
        if len(ficheiros_deste_chunk) < TOTAL_HOSPITALS:
            print(f"{chunk_name} ({ronda}): Faltam hospitais. Temos {len(ficheiros_deste_chunk)}/{TOTAL_HOSPITALS}.")
            continue
            
        print(f"SUCESSO! Temos os {TOTAL_HOSPITALS} hospitais para o {chunk_name}.")

        # APLICAR O LOCK
        print(f"A criar Lock de segurança para {chunk_name}...")
        s3_client.put_object(Bucket=bucket, Key=lock_key, Body=b'locked')

        # 2. CARREGAMENTO DO CONTEXTO CRIPTOGRÁFICO
        print("Sincronização aprovada. A preparar o ambiente TenSEAL...")
        s3_context_key = 'keys/public_context.bytes'
        local_context_path = '/tmp/public_context.bytes'
        
        try:
            s3_client.download_file(bucket, s3_context_key, local_context_path)
            with open(local_context_path, 'rb') as f:
                public_context = ts.context_from(f.read())
            print("Contexto Público FHE carregado com sucesso na Lambda!")
            
        except Exception as e:
            erro_msg = f"Erro fatal ao tentar descarregar o public_context.bytes: {str(e)}"
            print(f"{erro_msg}")
            s3_client.delete_object(Bucket=bucket, Key=lock_key)
            continue
            
        # 3. AGREGAÇÃO HOMOMÓRFICA (FASE Final)
        print(f"A descarregar e a somar fatias FHE para o {chunk_name}...")
        try:
            sum_vector = None

            for file_key in ficheiros_deste_chunk:
                s3_response = s3_client.get_object(Bucket=bucket, Key=file_key)
                chunk_bytes = s3_response['Body'].read()
                client_vector = ts.ckks_vector_from(public_context, chunk_bytes)

                if sum_vector is None:
                    sum_vector = client_vector
                else:
                    sum_vector += client_vector

            avg_vector = sum_vector * (1 / TOTAL_HOSPITALS)

            # Transformação direta para bytes puras (sem envolver numpy array)
            serialized_result = avg_vector.serialize()

            print(f"Upload do resultado final para {aggregated_key}...")
            s3_client.put_object(Bucket=bucket, Key=aggregated_key, Body=serialized_result)

            s3_client.delete_object(Bucket=bucket, Key=lock_key)
            print(f"Agregação concluída com SUCESSO ABSOLUTO para {chunk_name}!")

        except Exception as e:
            erro_msg = f"Erro durante a matemática FHE ou S3 IO: {str(e)}"
            print(f"{erro_msg}")
            s3_client.delete_object(Bucket=bucket, Key=lock_key)
            continue

    return {
        'statusCode': 200,
        'body': json.dumps('Processamento de batch S3 concluído.')
    }
