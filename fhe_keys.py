import tenseal as ts
import os

# Pasta onde vamos guardar as chaves (o volume Docker partilhado vai apanhar isto)
KEYS_DIR = "fhe_keys_data"

def setup_fhe_context():
    print("A iniciar a geração do Contexto Criptográfico CKKS (TenSEAL)...")
    
    # 1. Definição dos Parâmetros CKKS
    poly_mod_degree = 8192
    coeff_mod_bit_sizes = [60, 40, 40, 60]
    
    # 2. Criação do Contexto
    context = ts.context(
        ts.SCHEME_TYPE.CKKS,
        poly_modulus_degree=poly_mod_degree,
        coeff_mod_bit_sizes=coeff_mod_bit_sizes
    )
    
    # 3. Escala Global (Precisão das casas decimais)
    context.global_scale = 2**40
    
    # 4. Gerar chaves de Relinearização (Obrigatórias para multiplicações em FHE)
    context.generate_relin_keys()
    
    # Garantir que a pasta existe
    os.makedirs(KEYS_DIR, exist_ok=True)
    
    # 5. SALVAR O CONTEXTO PRIVADO (Com Secret Key) -> PARA OS HOSPITAIS
    # Os Hospitais precisam da Secret Key para cifrar os pesos iniciais
    # e para decifrar o modelo global no final de cada ronda.
    secret_context_path = os.path.join(KEYS_DIR, "secret_context.bytes")
    with open(secret_context_path, "wb") as f:
        # Serializamos com save_secret_key=True
        f.write(context.serialize(save_secret_key=True))
    print(f"Contexto Privado guardado em: {secret_context_path}")

    # 6. SALVAR O CONTEXTO PÚBLICO (Sem Secret Key) -> PARA A CLOUD/SERVER
    # O Servidor/AWS Lambda não pode ter acesso à Secret Key. 
    # A função make_context_public() destrói a chave privada deste objeto em memória.
    context.make_context_public()
    
    public_context_path = os.path.join(KEYS_DIR, "public_context.bytes")
    with open(public_context_path, "wb") as f:
        f.write(context.serialize())
    print(f"Contexto Público guardado em: {public_context_path}")
    
    print("Geração de chaves concluída com sucesso! Prontos para a Etapa de Cifragem.")

if __name__ == "__main__":
    setup_fhe_context()