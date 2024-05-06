

import os
import sys
import subprocess

from . import wpm_internal_utils
# stupid git problems:
# https://stackoverflow.com/questions/34820975/git-clone-redirect-stderr-to-stdout-but-keep-errors-being-written-to-stderr
# https://mirrors.edge.kernel.org/pub/software/scm/git/docs/git-clone.html

def download_github_repository(destination_path, zipurl, token, branch_name):

	headers = {
		"Authorization": f"token {token}",
		"Accept": "application/vnd.github.v3+json"
	}

	response = requests.get(zipurl, headers=headers)
	if response.status_code != 200:
		print(f"Failed to download {zipurl}")
		return

	with zipfile.ZipFile(io.BytesIO(response.content)) as z:
		for member in z.infolist():
			if member.is_dir():
				continue
			file_path = os.path.join(destination_path, os.path.relpath(member.filename, member.filename.split('/')[0]))
			print(f"extracting: {file_path}")
			os.makedirs(os.path.dirname(file_path), exist_ok=True)
			zf = z.open(member, 'r')
			of = open(file_path, 'wb')
			shutil.copyfileobj(zf, of)
			zf.close()
			of.close()

def get_git_delta_cwd(branch, abs_path):
	delta = wpm_internal_utils.run_silent_command("git rev-list --left-right --count " + branch + "...origin/" + branch, abs_path).replace("\n", "").replace("\t"," ")
	delta = [x for x in delta.split(" ") if x != ""]

	delta_msg = []

	if delta:
		if delta[0] != "0":
			delta_msg.append("ahead:" + delta[0])
		if delta[1] != "0":
			delta_msg.append("behind:" + delta[1])

	if delta_msg:
		delta_msg = "/".join(delta_msg)
	else:
		delta_msg = ""

	return delta_msg

def get_git_status_internal(abs_path, fast):

	if fast == False:
		wpm_internal_utils.run_silent_command("git remote update", abs_path)

	branch = wpm_internal_utils.run_silent_command("git rev-parse --abbrev-ref --symbolic-full-name HEAD", abs_path).replace("\n","")
	dirty = wpm_internal_utils.run_silent_command("git status --short", abs_path).replace(" ","").replace("\n","").replace("\t","")

	if fast == True:
		return branch, None, dirty, None

	current_hash = wpm_internal_utils.run_silent_command("git rev-parse HEAD 2> /dev/null | head -c 64", abs_path).replace("\n","")

	if branch == "HEAD":
		return branch, current_hash, dirty, ""
	
	delta = get_git_delta_cwd(branch, abs_path);

	return branch, current_hash, dirty, delta

def get_git_status(git_model, install_path, fast):
	branch, git_hash, dirty, delta = get_git_status_internal(install_path, fast)

	status = wpm_internal_utils.PackageStatusMessage()

	if dirty != "":
		# has local changes (uncommited)
		status.marker = "*"
		status.status = "DIRTY"
		status.info = f"git:{branch}"
	elif delta != None and delta != "":
		status.marker = "!"
		status.status = "DIRTY"
		status.info = f"git:{branch}"
	else:
		status.marker = " "
		status.status = "ok"
		status.info = f"git:{branch}"

	if fast == False:
		if dirty != "":
			status.info = f"{status.info} ({git_hash}) {delta}"
		elif delta != "":
			status.info = f"{status.info} ({git_hash}) {delta}"
			status.updatable = True
		else:
			status.info = f"{status.info} ({git_hash})"

	return status


def refresh_git(abs_path, fast, workspace):
	#first add as safe directory
	wpm_internal_utils.run_silent_command("git config --global --add safe.directory " + abs_path, workspace)

	if fast == True:
		return

	#second revert empty file changes
	from git import Repo

	repo = Repo(abs_path)

	if repo.bare:
		return

	def check_for_empty_changes(file_path):
		diffs = repo.git.diff('HEAD', file_path)
		if ("new mode" in diffs or "old mode" in diffs):
			for line in diffs.split('\n'):
				if(line.startswith('+') or line.startswith('-')):
					return False
			return True

		return False

	for item in repo.index.diff(None):
		if item.change_type != 'M':
			continue

		if check_for_empty_changes(item.a_path):
			print(f"Fixing '{item.a_path}'")
			repo.git.checkout('--', item.a_path)

def git_add_safe_command(workspace, entry):
	path = entry.get_install_path(workspace);

	command = f"git config --global --add safe.directory {path};"

	return command

def git_user_command(workspace, entry):
	path = entry.get_install_path(workspace);

	command = f"cd {path};"
	model = entry.model
	if model.user_name != None:
		command += f"cd {path};git config --local user.name \"{model.user_name}\";"
	if model.user_email != None:
		command += f"cd {path};git config --local user.email \"{model.user_email}\";"

	return command

def install_bucket(url, abspath, folder):
	from git import Repo
	from git.exc import GitCommandError

	model = entry.model
	url = entry.get_clone_url()
	install_folder = entry.get_install_parent_folder(workspace)
	
	if not os.path.exists(install_folder):
		os.makedirs(install_folder)

	try:
		tdir = os.path.join(install_folder, entry.name)
		repo = Repo.clone_from(url, os.path.join(install_folder, entry.name))

		# Check out the specified branch
		branch = model.active_branch
		if model.locked != None:
			branch = model.locked
		
		repo.git.checkout(branch)

		command = ""		
		command += git_add_safe_command(workspace, entry)
		command += git_user_command(workspace, entry)
	
		rc = wpm_internal_utils.run_command_and_wait(command, workspace, True)
		if rc != 0:
			return False


		return True
	except GitCommandError as e:
		print(f"Error cloning repository: {e}")
		return False

	except Exception as ex:
		print(f"Error:{e}")
		return false


def install_git_entry(workspace, entry):
	from git import Repo
	from git.exc import GitCommandError

	model = entry.model
	url = entry.get_clone_url()
	install_folder = entry.get_install_parent_folder(workspace)
	
	if not os.path.exists(install_folder):
		os.makedirs(install_folder)

	try:
		tdir = os.path.join(install_folder, entry.name)
		repo = Repo.clone_from(url, os.path.join(install_folder, entry.name))

		# Check out the specified branch
		branch = model.active_branch
		if model.locked != None:
			branch = model.locked
		
		repo.git.checkout(branch)

		command = ""		
		command += git_add_safe_command(workspace, entry)
		command += git_user_command(workspace, entry)
	
		rc = wpm_internal_utils.run_command_and_wait(command, workspace, True)
		if rc != 0:
			return False


		return True
	except GitCommandError as e:
		print(f"Error cloning repository: {e}")
		return False

	except Exception as ex:
		print(f"Error:{e}")
		return false


	


def create_install_command(url, model, name):
	if model.locked != None:
		command = ""
		command += f"git clone {url} {name};"
		command += f"git checkout {model.locked};"

		return command

	else:
		return f"git clone --branch {model.active_branch} --single-branch --depth 1 {url} {name};"
