package terraform.policy

import rego.v1

resources contains r if {
	walk(input.planned_values, [path, value])
	path[count(path) - 1] == "resources"
	some r in value
}

is_valid_dynamodb_table if {
	some r in resources
	r.type == "aws_dynamodb_table"
	r.values.name == "user-sessions"
}

is_valid_billing_mode if {
	some r in resources
	r.type == "aws_dynamodb_table"
	r.values.billing_mode == "PAY_PER_REQUEST"
}

is_valid_hash_key if {
	some r in resources
	r.type == "aws_dynamodb_table"
	r.values.hash_key == "session_id"
	some attr in r.values.attribute
	attr.name == "session_id"
	attr.type == "S"
}

is_valid_point_in_time_recovery if {
	some r in resources
	r.type == "aws_dynamodb_table"
	some pitr in r.values.point_in_time_recovery
	pitr.enabled == true
}
