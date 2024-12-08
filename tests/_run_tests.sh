#!/bin/bash

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"


REPODIR=$THIS_DIR/../
TEST_ENV_NAME=wpm-tests

docker build -t $TEST_ENV_NAME -f $THIS_DIR/test-env.dockerfile $THIS_DIR

docker run \
	--rm \
	-it \
	-v $REPODIR:/repo \
	-e "TERM=xterm-256color" \
	$TEST_ENV_NAME \
	/bin/bash /repo/tests/main_tests_entrypoint.sh

