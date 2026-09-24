#!/usr/bin/env bash
case "$1" in
  version) echo "Terraform v1.12.0 (fake)";;
  init) exit 0;;
  validate) echo '{"format_version":"1.0","valid":true,"error_count":0,"diagnostics":[]}'; exit 0;;
  plan) echo "Plan: 3 to add"; touch plan.bin; exit 0;;
  show) cat <<'JSON'
{"planned_values":{"root_module":{"resources":[
 {"type":"aws_s3_bucket","name":"b","values":{"bucket":"app-artifacts-2026"}},
 {"type":"aws_s3_bucket_versioning","name":"v","values":{"versioning_configuration":[{"status":"Enabled"}]}},
 {"type":"aws_s3_bucket_server_side_encryption_configuration","name":"e","values":{"rule":[{"apply_server_side_encryption_by_default":[{"sse_algorithm":"AES256"}]}]}}
]}}}
JSON
  exit 0;;
esac
exit 1
