import tenseal as ts
import time

try:
    print("A inicializar Contexto FHE Gigante (N=262144)...")
    # Tentar forçar o grau monolítico
    context = ts.context(ts.SCHEME_TYPE.CKKS, poly_modulus_degree=262144, coeff_mod_bit_sizes=[60, 40, 60])
    context.global_scale = 2**40
    context.generate_galois_keys()
    
    print("Contexto criado com sucesso! (Isto seria um milagre)")
    
    # Criar um array com 89.000 pesos falsos
    pesos_rede = [0.5] * 89000
    
    start = time.time()
    print("A cifrar 89.000 parâmetros de uma só vez...")
    vetor_cifrado = ts.ckks_vector(context, pesos_rede)
    print(f"Tempo de Cifragem: {time.time() - start:.2f} segundos")
    
except Exception as e:
    print(f"O SISTEMA FALHOU COMO PREVISTO: {e}")