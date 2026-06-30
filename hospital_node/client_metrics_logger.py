import csv
import os
from datetime import datetime

# Configurações de Métricas Locais (Edge)
# Este ficheiro está a ser gravado num volume partilhado do Docker
# para que os 3 hospitais escrevam no mesmo ficheiro do PC.
CSV_FILENAME = 'client_ml_metrics.csv'

def log_client_metrics(ronda, hospital_id, accuracy, loss, enc_time_ms, dec_time_ms, end_to_end_time_ms):
    """
    Grava as métricas de Machine Learning e Criptografia de um hospital numa ronda específica.
    
    Parâmetros:
    - ronda (int): O número da ronda atual de Federated Learning.
    - hospital_id (str/int): O identificador do hospital (ex: 'Hospital_1').
    - accuracy (float): A precisão global do modelo validada localmente (0.0 a 1.0).
    - loss (float): O valor da função de perda (Loss) nesta ronda.
    - enc_time_ms (float): Tempo que o TenSEAL demorou a cifrar os pesos localmente.
    - dec_time_ms (float): Tempo que o TenSEAL demorou a decifrar o modelo agregado recebido.
    - end_to_end_time_ms (float): Tempo total desde o início do treino até à receção do modelo global.
    """
    
    ficheiro_existe = os.path.isfile(CSV_FILENAME)
    timestamp_agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        # Usamos mode='a' para acrescentar linhas sem apagar o histórico
        with open(CSV_FILENAME, mode='a', newline='') as file:
            writer = csv.writer(file)
            
            # Criar o cabeçalho se for a primeira vez que o ficheiro é criado
            if not ficheiro_existe:
                writer.writerow([
                    'Timestamp', 
                    'Ronda', 
                    'Hospital_ID', 
                    'Global_Accuracy', 
                    'Global_Loss', 
                    'Encrypt_Time_ms', 
                    'Decrypt_Time_ms', 
                    'End_to_End_Round_Time_ms'
                ])
            
            # Gravar a linha de dados da ronda atual
            writer.writerow([
                timestamp_agora,
                ronda,
                hospital_id,
                round(accuracy, 4),      # Arredondado a 4 casas decimais para rigor científico
                round(loss, 4),
                round(enc_time_ms, 2),   # Arredondado a 2 casas decimais (milissegundos)
                round(dec_time_ms, 2),
                round(end_to_end_time_ms, 2)
            ])
            
        print(f"[{hospital_id}] Métricas da Ronda {ronda} gravadas com sucesso em {CSV_FILENAME}")
        
    except Exception as e:
        print(f"[{hospital_id}] Erro ao gravar métricas locais: {str(e)}")

# Exemplo de Integração (Como usar no teu código do Hospital)
if __name__ == "__main__":
    import time
    
    # 1. No início da ronda do teu hospital, marcas o tempo:
    inicio_ronda = time.time()
    
    print("A treinar modelo localmente...")
    time.sleep(0.5) # Simulação de treino...
    
    # 2. Quando fores cifrar com TenSEAL, medes o tempo:
    inicio_enc = time.time()
    print("A cifrar pesos com TenSEAL...")
    time.sleep(1.2) # Simulação da cifragem (chunking)...
    tempo_enc_ms = (time.time() - inicio_enc) * 1000
    
    print("A enviar para S3 e a aguardar agregação na AWS...")
    time.sleep(2.0) # Simulação do tempo de rede e AWS
    
    # 3. Quando receberes o agregado e fores decifrar:
    inicio_dec = time.time()
    print("A decifrar pesos agregados...")
    time.sleep(0.8) # Simulação da decifragem...
    tempo_dec_ms = (time.time() - inicio_dec) * 1000
    
    # 4. Cálculo do tempo total e métricas de ML simuladas
    tempo_total_ms = (time.time() - inicio_ronda) * 1000
    accuracy_simulada = 0.8543
    loss_simulada = 0.3120
    
    # 5. CHAMADA FINAL DA FUNÇÃO PARA GUARDAR OS DADOS
    log_client_metrics(
        ronda=1,
        hospital_id="Hospital_1",
        accuracy=accuracy_simulada,
        loss=loss_simulada,
        enc_time_ms=tempo_enc_ms,
        dec_time_ms=tempo_dec_ms,
        end_to_end_time_ms=tempo_total_ms
    )