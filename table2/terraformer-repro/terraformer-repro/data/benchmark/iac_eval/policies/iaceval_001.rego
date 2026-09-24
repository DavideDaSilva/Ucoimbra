package terraform.policy

import rego.v1

resources contains r if {
	walk(input.planned_values, [path, value])
	path[count(path) - 1] == "resources"
	some r in value
}

is_valid_lambda_function if {
	some r in resources
	r.type == "aws_lambda_function"
	r.values.function_name == "image-resizer"
}

is_valid_runtime if {
	some r in resources
	r.type == "aws_lambda_function"
	r.values.runtime == "python3.12"
}

is_valid_handler if {
	some r in resources
	r.type == "aws_lambda_function"
	r.values.handler == "index.handler"
}

is_valid_execution_role if {
	some r in resources
	r.type == "aws_iam_role"
}
