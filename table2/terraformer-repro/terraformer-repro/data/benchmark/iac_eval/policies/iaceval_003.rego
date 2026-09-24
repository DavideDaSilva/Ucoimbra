package terraform.policy

import rego.v1

resources contains r if {
	walk(input.planned_values, [path, value])
	path[count(path) - 1] == "resources"
	some r in value
}

is_valid_log_group if {
	some r in resources
	r.type == "aws_cloudwatch_log_group"
	r.values.name == "/aws/app/prod"
}

is_valid_retention if {
	some r in resources
	r.type == "aws_cloudwatch_log_group"
	r.values.retention_in_days == 30
}

is_valid_sns_topic if {
	some r in resources
	r.type == "aws_sns_topic"
	r.values.name == "alerts-topic"
}
