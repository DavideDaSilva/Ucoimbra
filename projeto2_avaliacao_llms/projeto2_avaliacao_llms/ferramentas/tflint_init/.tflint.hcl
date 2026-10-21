# Regras usadas pelo TFLint (Linter Pass Rate).
#
# plugin "terraform": regras gerais do Terraform. O preset "recommended" e o
#                     padrao do proprio TFLint.
# plugin "aws"      : regras especificas da AWS (ex.: tipo de instancia invalido).
#
# Para mudar a versao do plugin AWS, altere "version" e rode de novo o
# comando de preparacao (ele executa "tflint --init").

plugin "terraform" {
  enabled = true
  preset  = "recommended"
}

plugin "aws" {
  enabled = true
  version = "0.40.0"
  source  = "github.com/terraform-linters/tflint-ruleset-aws"
}
