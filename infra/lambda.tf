# 1. Empacotar o nosso código Python num ficheiro ZIP (O Lambda exige isto)
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/lambda_aggregator"
  output_path = "${path.module}/lambda_function.zip"
}

# 2. O Crachá de Segurança (IAM Role) para o Lambda
# O Lambda precisa de permissão oficial para existir e escrever nos logs.
resource "aws_iam_role" "lambda_exec_role" {
  name = "fhe_lambda_execution_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

# 3. Dar permissão ao Lambda para ler e escrever no teu S3 e nos Logs
resource "aws_iam_role_policy_attachment" "lambda_policy" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = "arn:aws:iam::aws:policy/AWSLambdaExecute"
}

# 4. Criar a Função Lambda em si!
resource "aws_lambda_function" "fhe_aggregator" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "fhe_chunk_aggregator"
  role             = aws_iam_role.lambda_exec_role.arn
  handler          = "lambda_function.lambda_handler"
  
  # Usamos Python 3.12 (o mais recente da AWS)
  runtime          = "python3.12"
  
  # Se o código do ZIP mudar, o Terraform atualiza o Lambda
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  # Damos-lhe alguma memória e tempo extra porque criptografia é pesada
  timeout          = 180
  memory_size      = 2048

  layers           = [aws_lambda_layer_version.tenseal_layer.arn]
}

# 5. Dizer ao S3 que ele tem permissão para "acordar" este Lambda
resource "aws_lambda_permission" "allow_s3_to_call_lambda" {
  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.fhe_aggregator.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.fhe_chunks_bucket.arn
}

# 6. O Gatilho! O gatilho que dispara o Lambda sempre que um .bytes entra no S3
resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket = aws_s3_bucket.fhe_chunks_bucket.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.fhe_aggregator.arn
    events              = ["s3:ObjectCreated:*"]
    filter_suffix       = ".bytes"
  }

  depends_on = [aws_lambda_permission.allow_s3_to_call_lambda]
}

# --- A nossa "Mochila" com o TenSEAL e NumPy ---
resource "aws_lambda_layer_version" "tenseal_layer" {
  filename            = "${path.module}/layer_build/tenseal_layer.zip"
  layer_name          = "tenseal_numpy_layer"
  compatible_runtimes = ["python3.12"]
  description         = "Layer com TenSEAL e NumPy compilados para Amazon Linux"
}