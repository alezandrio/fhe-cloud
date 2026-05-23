# 1. Avisar o Terraform que vamos usar a AWS
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# 2. Configurar a região (A mesma que puseste no AWS CLI)
provider "aws" {
  region = "eu-west-1"
}

# 3. Gerar um código aleatório (Os nomes dos buckets S3 têm de ser únicos no mundo todo!)
resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# 4. Criar o nosso Disco Rígido (S3 Bucket)
resource "aws_s3_bucket" "fhe_chunks_bucket" {
  bucket = "fhe-cloud-chunks-${random_id.bucket_suffix.hex}"

  force_destroy = true

  # Etiquetas para sabermos a quem pertence isto se a Amazon nos perguntar
  tags = {
    Name        = "Armazem de Fatias FHE"
    Environment = "Tese-Mestrado"
    Project     = "Federated Learning"
  }
}

# 5. Pedir ao Terraform para nos cuspir o nome exato do bucket no final
output "nome_do_bucket" {
  value       = aws_s3_bucket.fhe_chunks_bucket.bucket
  description = "Este é o nome que o nosso cliente Python vai precisar para enviar os dados."
}

# 6. Fazer o upload do Contexto Público FHE para a Cloud
resource "aws_s3_object" "public_context_file" {
  # Aponta para o bucket que acabámos de criar
  bucket = aws_s3_bucket.fhe_chunks_bucket.id
  
  # O caminho/nome do ficheiro como vai ficar guardado no S3
  key    = "keys/public_context.bytes" 
  
  # O caminho do ficheiro na tua máquina local (ajusta se a tua pasta local tiver outro nome)
  source = "../fhe_keys_data/public_context.bytes" 
  
  # Força o Terraform a atualizar o ficheiro no S3 sempre que o alterares localmente
  etag   = filemd5("../fhe_keys_data/public_context.bytes") 
}