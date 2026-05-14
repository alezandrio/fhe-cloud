#  FHE-Cloud: Serverless MapReduce for Federated Learning

**Projeto Final de Cloud Computing (LEI, 2025/26) - ISPGAYA**

Uma Prova de Conceito (PoC) que resolve os estrangulamentos de memória (RAM) e *Timeouts* na agregação de modelos de *Federated Learning* cifrados homomorficamente, utilizando uma arquitetura MapReduce em ambiente AWS Serverless.

 **Equipa:** Afonso Cruz, Vasco Carvalho, Carlos Marques

---

## Arquitetura do Projeto
O projeto está dividido em duas frentes:
1. **Edge (Local):** Simulação de hospitais heterogéneos via `Docker Compose` (treino local e cifragem de pesos com TenSEAL).
2. **Cloud (AWS):** Agregação paralela via `AWS Lambda`, `S3` e `EventBridge` usando o padrão de fatiamento (*Chunking* / MapReduce).

---

## Como arrancar o projeto na tua máquina

### 1. Pré-requisitos
* **Git** instalado.
* **Docker** e **Docker Compose** instalados (essencial para simular os hospitais).
* **Python 3.10+** instalado.

### 2. Clonar e Preparar o Ambiente
Abre o terminal e executa os seguintes passos:
```bash
# 1. Clonar o repositório
git clone <URL_DO_REPOSITORIO>
cd FHE-Cloud-Project

# 2. Criar e ativar o ambiente virtual isolado (NUNCA usar o Python global!)
python3 -m venv venv
source venv/bin/activate  # No Windows usa: venv\Scripts\activate

# 3. Instalar as dependências do Python
pip install --upgrade pip
pip install -r requirements.txt

**3. Levantar a Infraestrutura Local (Hospitais):**
```bash
docker compose up -d --build

## Regras de Ouro da Equipa!)
1. **NUNCA fazer commit de credenciais AWS:** Qualquer ficheiro `.env` ou chaves da AWS estão estritamente proibidos de vir parar ao GitHub.
2. **NUNCA fazer commit de ficheiros .bin gigantes:** Os *chunks* cifrados vão ter Gigabytes de tamanho. O nosso `.gitignore` já está configurado para os ignorar.
3. **Sincronização:** Antes de começarem a programar, façam sempre `git pull` para garantir que têm a versão mais recente do código dos colegas.
