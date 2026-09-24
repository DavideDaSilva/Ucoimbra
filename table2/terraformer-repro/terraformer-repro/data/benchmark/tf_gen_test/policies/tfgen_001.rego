# ===========================================================================
# POLITICA FORMAL (FL policy) - instancia tfgen_001
# ---------------------------------------------------------------------------
# Esta politica funciona como um TESTE UNITARIO da infraestrutura.
# Ela recebe como entrada (input) o JSON do `terraform plan` e verifica se o
# que o modelo gerou realmente atende a intencao do prompt.
#
# CONVENCAO DO PROJETO (importante):
#   1. O pacote e sempre `terraform.policy`.
#   2. Toda regra de verificacao tem nome que comeca com `is_valid_`.
#   3. Cada regra `is_valid_*` vale 1 ponto. A nota da instancia e
#      (regras que passaram) / (total de regras `is_valid_*`).
#   4. Correctness exige que TODAS as regras passem.
# ===========================================================================

package terraform.policy

import rego.v1

# Coleta todos os recursos planejados, inclusive os de modulos filhos.
resources contains r if {
	walk(input.planned_values, [path, value])
	path[count(path) - 1] == "resources"
	some r in value
}

is_valid_s3_bucket if {
	some r in resources
	r.type == "aws_s3_bucket"
	r.values.bucket == "app-artifacts-2026"
}

is_valid_versioning if {
	some r in resources
	r.type == "aws_s3_bucket_versioning"
	some cfg in r.values.versioning_configuration
	lower(cfg.status) == "enabled"
}

is_valid_encryption if {
	some r in resources
	r.type == "aws_s3_bucket_server_side_encryption_configuration"
	some rule in r.values.rule
	some default in rule.apply_server_side_encryption_by_default
	default.sse_algorithm == "AES256"
}
