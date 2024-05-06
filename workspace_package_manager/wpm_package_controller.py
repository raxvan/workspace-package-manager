
import os
import sys
import time
import json
from . import wpm_internal_utils

_colors = wpm_internal_utils.Colors

#####################################################################################################

class PackageMetadata():
	def __init__(self):
		self.dependencies = []

#####################################################################################################

class PackageActions():
	def __init__(self, abs_file_path, pack):
		self.path = abs_file_path
		self.actions = None
		self.pack = pack

	def init(self):
		f = open(self.path, "r")
		self.contents = json.load(f)
		f.close()

	#def evaluate_dependencies(self):
	#	return self.contents.get("+", [])

#####################################################################################################

class WorkspaceController():
	def __init__(self, workspace, packs):
		self.workspace = workspace
		self.packs = packs

	def _process_install(self, package, start_time):
		actions = package.get_actions(self.workspace)
		if actions != None:
			print(f"{_colors.LIGHT_BLUE}-- do(install):{_colors.END} {package_file}")
			duration = wpm_internal_utils.compute_duration(start_time)
			print(f"{_colors.LIGHT_GREEN}-- {_colors.BOLD}OK{_colors.END} {_colors.DARK_GRAY}({duration}){_colors.END}")
			
			return acc
		else:
			duration = wpm_internal_utils.compute_duration(start_time)
			print(f"{_colors.LIGHT_GREEN}-- {_colors.BOLD}OK{_colors.END} {_colors.DARK_GRAY}({duration}){_colors.END}")

		return None

	def install_one(self, package_name_ref, force, skip):

		start_time = time.time()
		package_info = self.packs.find(package_name_ref)
		if (package_info == None):
			raise Exception(f"Could not find package: {package_name_ref}")

		install_path = package_info.get_install_path(self.workspace)

		already_installed = os.path.exists(install_path)

		if already_installed:
			if skip:
				print(f"{_colors.LIGHT_BLUE}-- skipping: {_colors.BOLD}{_colors.LIGHT_WHITE}{package_name_ref}{_colors.END} -> {install_path}")
				return self._process_install(package_info, start_time)

			if force:
				print(f"{_colors.LIGHT_BLUE}-- removing:{_colors.END} {install_path}", end="")
				wpm_internal_utils.actually_remove_folder(install_path)
				print(" (done)")
			else:
				raise Exception(f"Package already installed at {install_path}")

		print(f"{_colors.LIGHT_BLUE}-- installing: {_colors.BOLD}{_colors.LIGHT_WHITE}{package_name_ref}{_colors.END} -> {install_path}")
		sys.stdout.flush()
		if package_info.install(self.workspace) == False:
			duration = wpm_internal_utils.compute_duration(start_time)
			print(f"{_colors.LIGHT_RED}-- {_colors.BOLD}ERROR{_colors.END} {_colors.DARK_GRAY}({duration}){_colors.END}")
			return

		return self._process_install(package_info, start_time)

	def install_loop(self, ref_queue, force, shallow, skip):
		install_queue = ref_queue.copy()
		install_names = set()

		while install_queue:
			name = install_queue.pop()

			actions = self.install_one(name, force, skip)
			if actions != None and shallow == False:
				dependencies = actions.evaluate_dependencies()
				install_queue.extend([dep for dep in dependencies if not dep in install_names])
			else:
				install_names.add(name)

#####################################################################################################

