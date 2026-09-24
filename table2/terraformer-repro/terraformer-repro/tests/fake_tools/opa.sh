#!/usr/bin/env bash
if [ "$1" = "version" ]; then echo "Version: 1.0.0 (fake)"; exit 0; fi
echo '{"result":[{"expressions":[{"value":{"is_valid_s3_bucket":true,"is_valid_versioning":true,"is_valid_encryption":true},"text":"data.terraform.policy"}]}]}'
exit 0
