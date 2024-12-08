
import os
import sys
import time
import json
import shutil
import argparse
import subprocess

from workspace_package_manager import wpm_internal_utils
from workspace_package_manager import wpm_package_database
from workspace_package_manager import wpm_package_controller

#####################################################################################################
#####################################################################################################

clrs = wpm_internal_utils.Colors

_env_search_locations = os.environ.get("WPM_SEARCH_LOCATIONS", None)
_env_worskace_path = os.environ.get("WPM_WORKSPACE_PATH", None)

def validate_search_locations(workspace):
	if _env_search_locations == None:
		return "No bucket search locations found"

	return None

def get_package_search_locations(workspace):
	return _env_search_locations.split(":")

def load_all_packages(workspace, silent):
	packs = wpm_package_database.PackageDatabase()

	logger = print
	if silent:
		logger = None

	loader = wpm_package_database.PackageDatabaseConstructor(packs, logger)
	
	bucket_list = get_package_search_locations(workspace)
	loader.load_bucket_list(workspace, bucket_list)

	return packs

#####################################################################################################
#####################################################################################################
#####################################################################################################

def _do_remove(workspace, package_name_ref):
	packs = load_all_packages(workspace, silent)

	package_info = packs.find(package_name_ref)
	if (package_info == None):
		raise Exception(f"Could not find package [{package_name_ref}] ...")

	ipath = package_info.get_install_path(workspace)
	if os.path.exists(ipath):
		print(f"{clrs.LIGHT_BLUE}-- removing:{clrs.END} {ipath}", end="")
		wpm_internal_utils.actually_remove_folder(ipath)
		print(" (done)")
	else:
		print(f"{clrs.LIGHT_RED}-- warning:{clrs.END} could not find install path {ipath}")

def _do_revision(workspace, silent, remoterev, package_name_ref):
	packs = load_all_packages(workspace, silent)

	package_info = packs.find(package_name_ref)
	if (package_info == None):
		raise Exception(f"Could not find package [{package_name_ref}] ...")

	rev = None
	if remoterev:
		rev = package_info.get_remote_revision()
	else:
		rev = package_info.get_installed_revision(workspace)

	print("-" * 48)
	print("    " + rev)
	print("-" * 48)

def _do_install(workspace, silent, package_name_ref, force, shallow, optional):
	packs = load_all_packages(workspace, silent)
	
	c = wpm_package_controller.WorkspaceController(workspace, packs)
	c.install_loop(package_name_ref, force, shallow, optional)

def _do_refresh(workspace, silent, fast):
	packs = load_all_packages(workspace, silent)
	items = os.listdir(workspace)
	items = sorted(items)
	for name in items:
		apath = os.path.join(workspace, name)
		
		package_info = packs.find(name)
		if package_info != None:
			print(f"SANITIZING: {package_info.name} ...")
			package_info.sanitize(workspace, fast)

	print("Done.")

def _do_update(workspace, silent, name):
	packs = load_all_packages(workspace, silent)
	package_info = packs.find(name)
	if package_info != None:
		ipath = package_info.get_install_path(workspace)
		if os.path.exists(ipath):
			print(f"UPDATING: {package_info.name} ...")
			package_info.update(workspace)
			print("Done.")
		else:
			print(f"MISSING INSTALL: wpm install {name} ...")
	else:
		print(f"MISSING PACKAGE: {name} ...")


def print_package_missing_status(pname):
	print("    " + (pname + " ").ljust(16,"-") + "> Missing...")

def print_ignored_status(abs_path, name):
	if os.path.isdir(abs_path):
		print(name.rjust(32) + f" | dir:{abs_path}")
	else:
		print(name.rjust(32) + f" | file:{abs_path}")

def print_unlisted_status(abs_path, name):
	if os.path.isdir(abs_path):
		print(name.rjust(32) + f" | dir:{abs_path}")
	else:
		print(name.rjust(32) + f" | file:{abs_path}")

def print_installed_package_status(workspace, package, fast):
	status_data = package.get_status(workspace, fast)

	start = status_data.status.rjust(8)

	message = f"{start}" + f"{status_data.marker} {package.name}".rjust(32) + f" | {status_data.info}"; 
	
	print(message)

	return status_data.updatable

def print_ok_status(abs_path, pname):
	print("    " + (pname + " ").ljust(16,"-") + "> Ok...")

def show_single_package_status(packs, workspace, name, fast):
	entry = packs.find(name)
	if entry != None:
		abspath = entry.get_install_path(workspace)
		if os.path.exists(abspath):
			print_installed_package_status(workspace, entry, fast);
		else:
			print_package_missing_status(entry.name)
	else:
		print(f"No such package `{name}`")
		return

def show_all_package_status(packs, workspace, fast):
	locations = {}
	for n, e in packs.getall():
		locations[e.get_install_path(workspace)] = e
	
	for i in os.listdir(workspace):
		l = os.path.join(workspace, i)
		if l in locations:
			continue
		locations[l] = i

	unlisted = []
	ignored = []
		
	for abspath, v in locations.items():
		if isinstance(v, str):
			if v.startswith("."):
				ignored.append((abspath, v))
			else:
				unlisted.append((abspath, v))
		elif os.path.exists(abspath):
				print_installed_package_status(workspace, v, fast);

	print ("UNLISTED:")
	for apath, name in unlisted:
		print_unlisted_status(apath, name)
	print ("IGNORED:")
	for apath, name in ignored:
		print_ignored_status(apath, name)


def _do_status(workspace, silent, name, fast):

	packs = load_all_packages(workspace, silent)

	if name != None:
		
		show_single_package_status(packs, workspace, name, fast)
		
	else:
		hworkspace = os.environ['HOST_WORKSPACE']
		print(f"WORKSPACE: {hworkspace}")

		show_all_package_status(packs, workspace, fast)

	#if show_update_commands == True:
	#	print ("Ready to update: " + workspace)
	#	for uc in update_commands:
	#		if uc != None:
	#			print(uc)

def _do_list(workspace : str, silent : bool, args):

	_showall = args.showall
	_showdef = args.showdef
	_showrev = args.showrev
	_showloc = False

	packs = load_all_packages(workspace, silent)

	names = sorted(packs.get_all_names())
	if not names:
		print("Missing packages")
		return
	maxname = max([len(n) for n in names]) + 4

	index = 1
	for n in names:
		
		p = packs.get(n)
		install_location = p.get_install_path(workspace)
		exists = os.path.exists(install_location)

		details = []

		if _showdef == True:
			details.append("def:" + p.get_definition_location())

		if exists == True:
			if _showloc == True:
				details.append("installed:"+ install_location)
			if _showrev == True:
				details.append("rev:" + p.get_installed_revision(workspace))
		elif _showall == True:
			if _showloc == True:
				extra_info.append("missing:"+ install_location)
		else:
			continue

		header = str(index).rjust(3) + " | " + n.rjust(maxname," ")
		if len(details) == 0:
			print(header)
		elif len(details) == 1:
			print(header + " | " + details[0])
		else:
			j = " " * (len(header) + 3)
			j = "\n" + j
			j = j.join(details)
			print(header + " > " + j)

		index += 1

def _exec_action(workspace, args):

	originalDirectory = os.getcwd()

	acc = args.action
	if acc == "install":
		_do_install(workspace, args.quiet, args.names, args.force, args.shallow, args.skip)
	elif acc == "refresh":
		_do_refresh(workspace, args.quiet, args.fast)
	elif acc == "update":
		_do_update(workspace, args.quiet, args.name)
	elif acc == "status":
		_do_status(workspace, args.quiet, args.name, args.fast)
	elif acc == "list":
		_do_list(workspace, args.quiet, args)
	elif acc == "remove":
		_do_remove(workspace, args.quiet, args.name)
	elif acc == "revision":
		_do_revision(workspace, args.quiet, args.remoterev, args.name)

	os.chdir(originalDirectory)

def find_wpm_directory(start_path):
	current_path = os.path.abspath(start_path)
	
	while True:
		wpm_path = os.path.join(current_path, '.wpm')
		if os.path.isdir(wpm_path):
			return current_path
		
		parent_path = os.path.dirname(current_path)
		
		if parent_path == current_path:
			break
		
		current_path = parent_path
	
	return None


def validate_workspace():
	workspace = None

	if _env_worskace_path != None and _env_worskace_path != "":
		workspace = _env_worskace_path

		if not os.path.exists(workspace):
			print(f"WPM_WORKSPACE_PATH variable points to missing folder {workspace}")
			exit(-1)

	if workspace == None:
		cwd = os.getcwd()
		workspace = find_wpm_directory(cwd)
		if workspace == None:
			print(f"{clrs.LIGHT_RED}WARNING:{clrs.YELLOW} workspace path is set to cwd: {workspace}{clrs.END}")
			workspace = cwd

	_sl_check = validate_search_locations(workspace)

	if _sl_check != None:
		print(_sl_check)
		exit(-1)

	os.makedirs(os.path.join(workspace,".wpm"), exist_ok = True)

	return workspace


def main():
	workspace = validate_workspace()

	user_arguments = sys.argv[1:]

	parser = argparse.ArgumentParser()
	parser.add_argument('-q', '--quiet', dest='quiet', action='store_true', help="Run in quiet mode.")

	subparsers = parser.add_subparsers(description='Actions:')

	install_parser = subparsers.add_parser('install', description='Installs or reinstall a package.')
	install_parser.set_defaults(action='install')
	install_parser.add_argument('-f', '--force', dest='force', action='store_true', help="Reinstall the package if already exists.")
	install_parser.add_argument('-s', '--shallow', dest='shallow', action='store_true', help="Install without any other depndencies.")
	install_parser.add_argument('-k', '--skip', dest='skip', action='store_true', help="Skip packages that are already installed")
	install_parser.add_argument('names', nargs='*', help='The namse of the package to install, see "list" command.')

	refresh_parser = subparsers.add_parser('refresh', description='Handles the removal of retarded garbage, run it at least once when you start working.')
	refresh_parser.set_defaults(action='refresh')
	refresh_parser.add_argument('-f', '--fast', dest='fast', action='store_true', help="Skip some steps in the refresh process to avoid waiting on large repositories")

	update_parser = subparsers.add_parser('update', description='Updates the package to latest')
	update_parser.set_defaults(action='update')
	update_parser.add_argument('name', default=None, help='Package name')

	revision_parser = subparsers.add_parser('revision', description='Prints the current revision of a package')
	revision_parser.set_defaults(action='revision')
	revision_parser.add_argument('-r', '--remote', dest='remoterev', action='store_true', help="Returns the remote revision")
	revision_parser.add_argument('name', default=None, help='The package name')

	list_parser = subparsers.add_parser('list', description='Lists package information.')
	list_parser.set_defaults(action='list')
	list_parser.add_argument('-a', '--all', dest='showall', action='store_true', help="Show all packages from database")
	list_parser.add_argument('-d', '--def', dest='showdef', action='store_true', help="Show package definition.")
	list_parser.add_argument('-r', '--rev', dest='showrev', action='store_true', help="shwo package revision.")

	status_parser = subparsers.add_parser('status', description='Shows status of packages in workspace and workspace')
	status_parser.set_defaults(action='status')
	status_parser.add_argument('-f', '--fast', dest='fast', action='store_true', help="Only show if repository is dirty.")
	status_parser.add_argument('name', nargs='?', default=None, help='The name of the package to install, see "list" command.')

	rm_parser = subparsers.add_parser('rm', description='remove a package')
	rm_parser.set_defaults(action='remove')
	rm_parser.add_argument('name', help='The name of the package to remove.')

	args = parser.parse_args(user_arguments)

	if hasattr(args, 'action'):
		_exec_action(workspace, args)
	else:
		print("Usage:")
		print("\t-> wpm [-q] ACTION [args]")
		print("ARGS:")
		print("\t-q : `quiet` mode, print less stuff.")
		print("ACTION Choices:")
		for k, _ in subparsers.choices.items():
			print(f"\t-> {k}")
		print("Workspace path (WPM_WORKSPACE_PATH):")
		print(f"\t-> {workspace}")
		print("Search search locations (WPM_SEARCH_LOCATIONS):")
		for p in get_package_search_locations(workspace):
			print(f"\t-> {p}")
	
	

