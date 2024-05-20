#!/bin/bash
set -e -o pipefail

cd /repo
pip install .

cd /repo/tests
rm -rf ./_tests_workspace ||:
mkdir _tests_workspace



echo "---------------------------------------------- STARTING VAULT:"
/bin/sh /pySecretsVault/vaultserver/entrypoint.sh > /repo/tests/_tests_workspace/output.log 2>&1 &

sleep 5

echo "---------------------------------------------- TEST 1:"
cd /repo/tests/workspace
vault set encoded_definition.jv testpass

cd /repo/tests
export WPK_SEARCH_LOCATIONS=/repo/tests/workspace
wpm
cd /repo/tests/workspace
wpm list -d

echo "---------------------------------------------- TEST 2:"
export WPK_SEARCH_LOCATIONS=/repo/tests/bucket1:/repo/tests/bucket2
export WPM_WORKSPACE_PATH=/repo/tests/_tests_workspace
wpm -q list -a

echo "---------------------------------------------- TEST 4(INSTALL):"
wpm -q install pack-pyr
wpm -q list -a -d
wpm -q install pack-pywr pack-json1 pack-json2
wpm -q list
echo "---------------------------------------------- TEST 5(REFRESH):"
wpm refresh