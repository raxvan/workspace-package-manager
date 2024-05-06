#!/bin/bash
set -e -o pipefail

cd /repo
pip install .

cd /repo/tests
rm -rf ./test_workspace ||:

mkdir test_workspace

echo "STARTING VAULT:"
/bin/sh /pySecretsVault/vaultserver/entrypoint.sh > /repo/tests/test_workspace/output.log 2>&1 &

sleep 5

export WPK_SEARCH_LOCATIONS=/repo/tests/bucket1:/repo/tests/bucket2

cd /repo/tests/test_workspace

wpm

cd /repo/tests

export WPM_WORKSPACE_PATH=/repo/tests/test_workspace

wpm

echo "LIST:"
wpm list -a
wpm install pack-pyr
wpm install pack-pywr pack-json1 pack-json2

wpm refresh