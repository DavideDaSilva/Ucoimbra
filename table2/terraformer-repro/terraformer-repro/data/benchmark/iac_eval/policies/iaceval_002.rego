package terraform.policy

import rego.v1

resources contains r if {
	walk(input.planned_values, [path, value])
	path[count(path) - 1] == "resources"
	some r in value
}

is_valid_security_group if {
	some r in resources
	r.type == "aws_security_group"
	r.values.name == "web-sg"
}

is_valid_vpc_attachment if {
	some r in resources
	r.type == "aws_vpc"
}

is_valid_https_ingress if {
	some r in resources
	r.type == "aws_security_group"
	some ing in r.values.ingress
	ing.from_port == 443
	ing.to_port == 443
}

is_valid_egress_all if {
	some r in resources
	r.type == "aws_security_group"
	some eg in r.values.egress
	eg.from_port == 0
	eg.to_port == 0
}
