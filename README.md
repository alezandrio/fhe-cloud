# ☁️ FHE Cloud: Federated Learning Serverless com Cifragem Homomórfica

Bem-vindos ao repositório do projeto de dissertação. Este sistema implementa uma arquitetura Híbrida (Edge-to-Cloud) para treinar modelos de Inteligência Artificial (Redes Neuronais) em dados médicos descentralizados (Hospitais), garantindo privacidade absoluta através de **Cifragem Homomórfica Total (FHE - TenSEAL)**.

## 🏗️ Arquitetura Atual (Fase 2 -> Fase 3)
Neste momento, a nossa infraestrutura funciona da seguinte forma:
1. **Nós Edge (Hospitais):** Simulados via Docker. Treinam o modelo localmente, fatiam os pesos da rede (chunks) para evitar esgotamento de RAM, cifram tudo com TenSEAL e enviam para a AWS S3.
2. **Data Lake (S3):** Atua como ponto de entrada (`incoming/`) e atua como gatilho orientado a eventos.
3. **Agregação Serverless (AWS Lambda):** Uma função Lambda com 2GB de RAM que acorda automaticamente quando os ficheiros entram no S3. O Lambda possui uma "Layer" especial com o código fonte em C++ do TenSEAL para conseguir fazer processamento pesado na nuvem a custo zero.

---

## 🚀 Guia Passo a Passo para Testar Localmente

Como não enviamos ficheiros binários pesados e ficheiros de configuração para o GitHub (boas práticas de segurança e CI/CD), precisas de preparar o teu ambiente local antes de correr o projeto.

### Pré-requisitos
- **Docker e Docker Compose** instalados.
- **AWS CLI (v2)** instalada e configurada com as chaves da conta (`aws configure`).
- **Terraform** instalado.
- Ferramenta **Zip** instalada no terminal (ex: `sudo apt install zip`).

---

### Passo 1: Compilar a "Mochila" Matemática (AWS Lambda Layer)
A AWS precisa da biblioteca TenSEAL pré-compilada para o sistema Linux deles. Como ignorámos este ficheiro pesado no Git, tens de o gerar na tua máquina:

1. Abre o terminal e navega para a pasta da build:
    cd infra/layer_build
2. Corre este comando para o Docker simular a nuvem, compilar a matemática e extrair as bibliotecas:
    docker run --rm -v $(pwd):/var/task public.ecr.aws/sam/build-python3.12 /bin/sh -c "pip install tenseal numpy -t python/"
3. Comprime o resultado no ficheiro ZIP que o Terraform vai ler:
    zip -r tenseal_layer.zip python
(Podes voltar à raiz do projeto com cd ../..)

Passo 2: Levantar a Infraestrutura Cloud (Terraform)

1. Entra na pasta do Terraform:
    cd infra
2. Inicializa e faz o deploy:
    terraform init -upgrade
    terraform apply -auto-approve
3. MUITO IMPORTANTE: No final, o terminal vai devolver a verde o nome_do_bucket (ex: fhe-cloud-chunks-xxxx). Copia esse nome! Vai ao ficheiro hospital_node/client.py e atualiza a variável BUCKET_NAME com o teu novo bucket (até automatizarmos isto com variáveis de ambiente).

Passo 3: Iniciar o Federated Learning (Treino Edge)

Com a nuvem pronta e à escuta, vamos ligar os hospitais.
1. Na raiz do projeto, arranca o ecossistema Docker:
    docker compose down
    docker compose up -d --build
2. Acompanha o trabalho dos hospitais no teu terminal:
    docker compose logs -f
(Deves ver mensagens a confirmar que cada hospital enviou as 22 fatias cifradas para o S3 com sucesso).

Passo 4: Monitorizar a Magia na Cloud (Opcional, mas recomendado)
Para provares que a nuvem está a reagir aos hospitais em tempo real:

1. Abre um segundo terminal.

2. Verifica se as fatias entraram na pasta segura do S3:
    aws s3 ls s3://COLA_AQUI_O_TEU_BUCKET/incoming/ --recursive
3. Vê os registos em direto do AWS Lambda a acordar e a atuar como Barreira de Sincronização:
    aws logs tail /aws/lambda/fhe_chunk_aggregator --follow --region eu-west-1

Próximos Desenvolvimentos (To-Do List)

A nossa prioridade atual foca-se na refatoração arquitetural reportada na auditoria de código:

    [ ] Remover a função de agregação matemática do servidor local (Flower).

    [ ] Enviar a chave pública (public_context.bytes) para o S3 para a AWS conseguir fazer a soma.

    [ ] Extrair o nome do bucket para o docker-compose.yml (os.getenv).

    [ ] Implementar controlo de concorrência (Race Conditions) no AWS Lambda.
    
