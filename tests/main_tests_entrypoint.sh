#!/bin/bash
set -e -o pipefail

cd /repo
pip install .

cd /repo/build

rm -rf ./_tests_workspace ||:

mkdir -p _tests_workspace

echo "---------------------------------------------- (LIST1):"
cd /repo/tests/workspace

echo "---->>>>> encoded_definition.jv password: 'testpass' !!!"

cd /repo/tests
export WPM_SEARCH_LOCATIONS=/repo/tests/workspace
wpm
cd /repo/tests/workspace
wpm list -d

echo "---------------------------------------------- (LIST2):"
export WPM_SEARCH_LOCATIONS=/repo/tests/bucket1:/repo/tests/bucket2
export WPM_WORKSPACE_PATH=/repo/build/_tests_workspace
wpm -q list -a

echo "---------------------------------------------- (INSTALL):"
wpm -q install pack-pyr
wpm -q list -a -d -r
wpm -q install pack-pywr pack-json1 pack-json2
wpm -q list
echo "---------------------------------------------- (REFRESH):"
wpm refresh

wpm -q revision pack-pyr
wpm -q revision -r pack-pyr


wpm update pack-pyr