☁️ FHE-Cloud: Plataforma Serverless MapReduce para Federated Learning
Visão Geral
Este projeto é uma Prova de Conceito (PoC) que demonstra como a fragmentação de dados (Chunking) e o processamento paralelo em arquiteturas Serverless (AWS MapReduce) resolvem os estrangulamentos de memória (Out-Of-Memory) e falhas de Timeout no treino de modelos de Inteligência Artificial. Utiliza Cifragem Homomórfica (FHE - algoritmo CKKS via TenSEAL) para garantir que os dados de treino de modelos médicos (MedMNIST) permanecem 100% privados.

--------------------------------------------------------------------------------
Estrutura do Repositório
Para manter uma arquitetura limpa, o repositório divide-se nas seguintes pastas principais:

    /hospital_node: Lógica dos nós Edge (Clientes Flower) simulados via Docker, responsáveis pelo treino local e cifragem.
    /server: Lógica do servidor orquestrador que coordena as rondas de treino.
    /infra: Ficheiros de Infraestrutura como Código (Terraform) para criar automaticamente a infraestrutura na AWS.


--------------------------------------------------------------------------------
Pré-Requisitos
Para testares este projeto, precisas de ter instalado no teu sistema:

    Para testares este projeto, precisas de ter instalado no teu sistema:
    * Docker e Docker Compose (Para simular os hospitais e compilar a Layer AWS).
    * Terraform (Para criar a infraestrutura na nuvem).
    * AWS CLI v2 (Para comunicar com a Amazon Web Services).
    * Python 3.10+ (Apenas para gerar as chaves locais de criptografia).


--------------------------------------------------------------------------------
## Guião de Setup Passo a Passo

### Passo 1: Configuração da Conta AWS e Permissões
Como o projeto utiliza a infraestrutura Serverless da Amazon (S3, EventBridge e Lambda), é necessário criar credenciais programáticas seguras.
1. Cria uma conta gratuita em `aws.amazon.com`.
2. Acede à Consola da AWS, pesquisa por **IAM** e navega até **Users**.
3. Clica em **Create user** e dá-lhe o nome `fhe-cloud-admin` (não dês acesso à consola web).
4. Na secção de permissões, escolhe "Attach policies directly" e seleciona a política **AdministratorAccess**.
5. Clica no utilizador criado, vai ao separador **Security credentials** e cria uma **Access key** selecionando a opção "Command Line Interface (CLI)".
6. **Importante:** Copia a *Access Key ID* e a *Secret Access Key* e guarda-as num local seguro.

### Passo 2: Ligação do Teu Computador à AWS
No terminal do teu computador, configura a ligação utilizando a ferramenta AWS CLI:
```bash
aws configure
Preenche os dados solicitados da seguinte forma:

    AWS Access Key ID: (A chave que acabaste de criar).

    AWS Secret Access Key: (O segredo que acabaste de criar).

    Default region name: eu-west-1 (Região da Irlanda).

    Default output format: json.

Passo 3: Compilar a Layer Criptográfica (x86_64)
Para garantir que a biblioteca TenSEAL funciona na AWS independentemente do teu processador local (Apple Silicon/ARM ou Intel), temos de compilar as dependências usando um emulador Linux.

cd infra/layer_build
docker run --rm --platform linux/amd64 -v $(pwd):/var/task public.ecr.aws/sam/build-python3.12 /bin/sh -c "pip install tenseal numpy -t python/"
zip -r tenseal_layer.zip python
cd ../..

Passo 4: Provisionar a Nuvem com Terraform e Extrair Variáveis
Agora vamos criar a nuvem (Lambda e o Bucket S3) onde os hospitais irão depositar os dados.

cd infra
terraform init
terraform apply
(Escreve yes quando solicitado).

Após o sucesso, o Terraform vai imprimir o nome gerado para o teu Bucket S3. Tens de exportar esse nome para que o Docker o injete nos hospitais:

export BUCKET_NAME=$(terraform output -raw nome_do_bucket)
cd ..

Passo 5: Gerar as Chaves de Cifragem Homomórfica
A biblioteca TenSEAL necessita de um par de chaves (Pública e Privada) para funcionar. Na raiz do projeto, executa:

python fhe_keys.py
(Isto criará a pasta fhe_keys_data com os ficheiros .bytes).

Passo 6: Arrancar a Simulação e Monitorizar a Cloud
Para veres o projeto em pleno funcionamento, recomendamos o uso de dois terminais.
Terminal 1 (Monitorizar a Matemática na Cloud):
Acompanha a agregação MapReduce em tempo real na AWS:

aws logs tail /aws/lambda/fhe_chunk_aggregator --follow --region eu-west-1

Terminal 2 (Arrancar o Federated Learning):
Na raiz do projeto, arranca os hospitais e o servidor:

docker-compose up --build

--------------------------------------------------------------------------------
Notas de Segurança

    Nunca faças commit das tuas credenciais da AWS para o GitHub. O ficheiro docker-compose.yml já está configurado para ler as tuas credenciais de forma segura através do volume ~/.aws:/root/.aws:ro em modo de leitura (Read-Only).
    Ficheiros .bytes e a diretoria .terraform são automaticamente excluídos pelo .gitignore definido no projeto para evitar corrupção e excesso de tamanho no repositório.