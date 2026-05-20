import json
import urllib.parse

def lambda_handler(event, context):
    # Esta função é ativada automaticamente pela AWS S3!
    
    # 1. Descobrir qual foi o ficheiro que acabou de fazer upload
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    
    print(f"O ficheiro '{key}' acabou de aterrar no bucket '{bucket}'.")
    
    # Mais tarde, vamos colocar aqui a matemática TenSEAL!
    
    return {
        'statusCode': 200,
        'body': json.dumps('Leitura feita com sucesso!')
    }