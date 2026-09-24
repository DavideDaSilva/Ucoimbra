package terraform.policy

import rego.v1

resources contains r if {
	walk(input.planned_values, [path, value])
	path[count(path) - 1] == "resources"
	some r in value
}

is_valid_main_queue if {
	some r in resources
	r.type == "aws_sqs_queue"
	r.values.name == "orders-queue"
}

is_valid_retention_period if {
	some r in resources
	r.type == "aws_sqs_queue"
	r.values.name == "orders-queue"
	r.values.message_retention_seconds == 345600
}

is_valid_encryption if {
	some r in resources
	r.type == "aws_sqs_queue"
	r.values.name == "orders-queue"
	r.values.sqs_managed_sse_enabled == true
}

is_valid_dead_letter_queue if {
	some r in resources
	r.type == "aws_sqs_queue"
	r.values.name == "orders-dlq"
}

is_valid_redrive_policy if {
	some r in resources
	r.type == "aws_sqs_queue"
	r.values.name == "orders-queue"
	contains(r.values.redrive_policy, "maxReceiveCount")
}
