package terraform.policy

import rego.v1

resources contains r if {
	walk(input.planned_values, [path, value])
	path[count(path) - 1] == "resources"
	some r in value
}

is_valid_vpc if {
	some r in resources
	r.type == "aws_vpc"
	r.values.cidr_block == "10.0.0.0/16"
}

is_valid_dns_hostnames if {
	some r in resources
	r.type == "aws_vpc"
	r.values.enable_dns_hostnames == true
}

is_valid_subnet if {
	some r in resources
	r.type == "aws_subnet"
	r.values.cidr_block == "10.0.1.0/24"
	r.values.availability_zone == "us-east-1a"
}

is_valid_internet_gateway if {
	some r in resources
	r.type == "aws_internet_gateway"
}
