#!/usr/bin/env bash
if [ "$1" = "--version" ]; then echo "3.2.0 (fake)"; exit 0; fi
echo '{"summary":{"passed":7,"failed":3,"skipped":0}}'
exit 0
