// ===========================================================================
// ARQUIVO DE OVERRIDE DO PROVIDER AWS
// ---------------------------------------------------------------------------
// Para que serve:
// O paper avalia o codigo Terraform ANTES de qualquer deploy real
// ("pre-deployment verification"). Nada e criado na nuvem de verdade.
// O comando `terraform plan`, porem, tenta por padrao falar com a AWS para
// validar credenciais e descobrir o ID da conta. Sem uma conta real isso
// falharia por motivo de credencial, e nao por erro do codigo gerado pelo
// modelo, o que estragaria a medicao.
//
// O Terraform trata qualquer arquivo terminado em "_override.tf" como um
// arquivo de sobreposicao: ele funde estes atributos no bloco `provider "aws"`
// que o modelo gerou, desligando as chamadas de rede.
//
// Este arquivo e copiado automaticamente para dentro da pasta de cada
// instancia avaliada. Voce pode desligar esse comportamento colocando
// aws.inject_provider_override = false no config/config.yaml.
// ===========================================================================

provider "aws" {
  region                      = "us-east-1"
  access_key                  = "mock_access_key"
  secret_key                  = "mock_secret_key"
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_region_validation      = true
  skip_requesting_account_id  = true
}
