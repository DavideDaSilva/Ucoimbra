package terraform.policy

import rego.v1

resources contains r if {
	walk(input.planned_values, [path, value])
	path[count(path) - 1] == "resources"
	some r in value
}

is_valid_iam_role if {
	some r in resources
	r.type == "aws_iam_role"
	r.values.name == "lambda-exec-role"
}

is_valid_assume_role_lambda if {
	some r in resources
	r.type == "aws_iam_role"
	contains(r.values.assume_role_policy, "lambda.amazonaws.com")
}

is_valid_logs_permission if {
	some r in resources
	r.type in {"aws_iam_role_policy", "aws_iam_policy"}
	contains(r.values.policy, "logs:")
}
