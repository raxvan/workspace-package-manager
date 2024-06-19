

set REPODIR=%~dp0../
set TEST_ENV_NAME=wpm-tests

robocopy %REPODIR%/../pySecretsVault %REPODIR%/build/pySecretsVault /E

docker build -t %TEST_ENV_NAME% -f %~dp0test-env.dockerfile %~dp0../
 
docker run ^
	-it ^
	--rm ^
	-v %REPODIR%:/repo ^
	-e "TERM=xterm-256color" ^
	%TEST_ENV_NAME% ^
	/bin/bash /repo/tests/main_tests_entrypoint.sh
