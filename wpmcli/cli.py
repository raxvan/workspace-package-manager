
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
_search_locations = os.environ.get("WPK_SEARCH_LOCATIONS", None)
_worskace_path = os.environ.get("WPM_WORKSPACE_PATH", None)

def validate_search_locations(workspace):
	if _search_locations == None:
		return "No bucket search locations found"

	return None

def get_package_search_locations(workspace):
	return _search_locations.split(":")

def _run_bucket_loading(workspace, loader):
	start = time.time()

	bucket_list = get_package_search_locations(workspace)
	print(f"{clrs.LIGHT_BLUE}-- workspace:{clrs.END} {clrs.PURPLE}{workspace}{clrs.END}")
	print(f"{clrs.LIGHT_BLUE}-- loading packages:{clrs.END}")

	#main definition in this repo
	for b in bucket_list:
		if os.path.exists(b):
			loader.load_bucket(b)

	duration = wpm_internal_utils.compute_duration(start)

	print(f"{clrs.LIGHT_GREEN}-- {clrs.BOLD}OK{clrs.END} {clrs.DARK_GRAY}({duration}){clrs.END}")
	print(clrs.DARK_GRAY + "-" * 64 + clrs.END)

def load_all_packages(workspace):
	packs = wpm_package_database.PackageDatabase()

	loader = wpm_package_database.PackageDatabaseConstructor(packs)

	_run_bucket_loading(workspace, loader)

	return packs

#####################################################################################################
#####################################################################################################
#####################################################################################################

def _do_remove(workspace, package_name_ref):
	packs = load_all_packages(workspace)

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

def _do_install(workspace, package_name_ref, force, shallow, optional):
	packs = load_all_packages(workspace)
	
	c = wpm_package_controller.WorkspaceController(workspace, packs)
	c.install_loop(package_name_ref, force, shallow, optional)

def _do_refresh(workspace, fast):
	packs = load_all_packages(workspace)
	items = os.listdir(workspace)
	items = sorted(items)
	for name in items:
		apath = os.path.join(workspace, name)
		
		package_info = packs.find(name)
		if package_info != None:
			print(f"SANITIZING: {package_info.name} ...")
			package_info.sanitize(workspace, fast)

	print("Done.")

def clean_files_recursive(directory):
	for i in os.listdir(directory):
		if i == ".git":
			continue

		path = os.path.join(directory, i)
		if os.path.isdir(path):
			clean_files_recursive(path)

		elif i == ".DS_Store":
			print(f"removing: {path}")
			os.remove(path)

def _do_clean(workspace):
	print("Cleaning files...")
	clean_files_recursive(workspace)
	print("Done.")

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

	return update_commands

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

	return update_commands

def _do_status(workspace, name, fast):

	packs = load_all_packages(workspace)

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

def _do_list(workspace : str, showall : bool, showdef: bool):

	packs = load_all_packages(workspace)

	names = sorted(packs.get_all_names())
	if not names:
		print("No packages found.")
		return
	maxname = max([len(n) for n in names]) + 4

	index = 1
	for n in names:
		
		p = packs.get(n)

		extra_info = ""
		if showdef == True:
			extra_info += f" def:{p.get_definition_location()}"
		
		install_location = p.get_install_path(workspace)
		exists = os.path.exists(install_location)

		if exists == True:
			extra_info += f" installed:{install_location}"
			print(str(index).rjust(3) + " | " + n.ljust(maxname," ") + extra_info)
			index += 1
		elif showall == True:
			extra_info += f" missing:{install_location}"
			print(str(index).rjust(3) + " | " + n.ljust(maxname," ") + extra_info)
			index += 1


def _do_install_command(workspace, package):
	packs = load_all_packages(workspace)
	package_info = packs.find(package)
	if (package_info == None):
		raise Exception("Could not find package: " + package)

	print(package_info.generate_install_command())

def _exec_action(workspace, args):

	originalDirectory = os.getcwd()

	acc = args.action
	if acc == "install":
		_do_install(workspace, args.names, args.force, args.shallow, args.skip)
	elif acc == "refresh":
		_do_refresh(workspace, args.fast)
	elif acc == "clean":
		_do_clean(workspace)
	elif acc == "status":
		_do_status(workspace, args.name, args.fast)
	elif acc == "list":
		_do_list(workspace, args.showall, args.showdef)
	elif acc == "remove":
		_do_remove(workspace, args.name)
	elif acc == "install-command":
		_do_install_command(workspace, args.name)

	os.chdir(originalDirectory)

def validate_workspace():
	workspace = _worskace_path
	if workspace == None:
		workspace = os.getcwd()
	elif not os.path.exists(workspace):
		print(f"WPM_WORKSPACE_PATH variable points to missing folder {workspace}")
		exit(-1)

	_sl_check = validate_search_locations(workspace)

	if _sl_check != None:
		print(_sl_check)
		exit(-1)

	return workspace


def main():
	workspace = validate_workspace()

	user_arguments = sys.argv[1:]

	parser = argparse.ArgumentParser()
	subparsers = parser.add_subparsers(description='Actions:')

	install_parser = subparsers.add_parser('install', description='Installs or reinstall a package.')
	install_parser.set_defaults(action='install')
	install_parser.add_argument('-f', '--force', dest='force', action='store_true', help="Reinstall the package if already exists.")
	install_parser.add_argument('-s', '--shallow', dest='shallow', action='store_true', help="Install without any other depndencies.")
	install_parser.add_argument('-k', '--skip', dest='skip', action='store_true', help="Skip packages that are already installed")
	install_parser.add_argument('names', nargs='*', help='The namse of the package to install, see "list" command.')

	install_command_parser = subparsers.add_parser('install-command', description='prints a command in terminal which allows you to install the package from a terminal')
	install_command_parser.set_defaults(action='install-command')
	install_command_parser.add_argument('name', default=None, help='The name of the package to install, see "list" command.')

	refresh_parser = subparsers.add_parser('refresh', description='Handles the removal of retarded garbage, run it at least one when you start working.')
	refresh_parser.set_defaults(action='refresh')
	refresh_parser.add_argument('-f', '--fast', dest='fast', action='store_true', help="Skip some steps in the refresh process to avoid waiting on large repositories")

	clean_parser = subparsers.add_parser('clean', description='Removes useless files from the workspace')
	clean_parser.set_defaults(action='clean')

	list_parser = subparsers.add_parser('list', description='Lists package information.')
	list_parser.set_defaults(action='list')
	list_parser.add_argument('-a', '--all', dest='showall', action='store_true', help="Show all packages from database")
	list_parser.add_argument('-d', '--def', dest='showdef', action='store_true', help="Show package definition")

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
		print("\t-> wpm ACTION [args]")
		print("ACTION Choices:")
		for k, _ in subparsers.choices.items():
			print(f"\t-> {k}")
		print("Workspace path (WPM_WORKSPACE_PATH):")
		print(f"\t-> {workspace}")
		print("Search search locations (WPK_SEARCH_LOCATIONS):")
		for p in get_package_search_locations(workspace):
			print(f"\t-> {p}")
	
	

