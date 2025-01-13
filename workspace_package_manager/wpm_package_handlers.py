
import os
import sys
import json
import zipfile
import io
import shutil
import importlib.util

from . import wpm_package_models
from . import wpm_internal_utils

class BucketDefinition():
	def __init__(self, parent, database, abs_path):
		self.parent = parent
		self.database = database
		self.folder, self.file = os.path.split(abs_path)
		self.abspath = abs_path
		
		self.props = {}

	def load_json_properties(self, jdict):
		self.props = jdict

	def load_json_requirements(self, l):
		for rprop in l:
			self.fetch_requirement(rprop)
		
	def get_property(self, name):
		if self.props != None:
			return self.props.get(name, None)
		if self.parent != None:
			return self.parent.get_property(name)

		return self.database.get_property(name)

	def set_property(self, pname, pvalue):
		self.props[pname] = str(pvalue)

	def has_property(self, pname):
		if pname in self.props:
			return True

		if self.parent != None:
			return self.parent.has_property(pname)
		
		return None #self.database.has_property(pname)

	def fetch_requirement(self, rname):
		if self.has_property(rname):
			return True

		m = self.database.try_resolve(rname)
		if m != None:
			self.set_property(rname, m)
			return True

		return False

	def get_all_properties(self):
		props = {}
		if self.parent != None:
			props.update(self.parent.get_all_properties())

		if self.props != None:
			props.update(self.props)

		return props

	def format_string_for_bucket(self, s):
		props = self.get_all_properties()
		#while True:
		try:
			return s.format(**props)
		except KeyError as e:

			raise Exception(f"Missing key in string {s}:{e}")

		except:
			raise


#######################################################################################################

class PackageActions:
	def __init__(self, name, abs_path_to_file):
		self.module = self.load_module_from_path(name, abs_path_to_file)

	@staticmethod
	def load_module_from_path(module_name, path_to_file):
		spec = importlib.util.spec_from_file_location(module_name, path_to_file)
		module = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(module)
		return module

	def run(self, name):
		func = getattr(self.module, name, None)
		if func != None:
			return func(), True

		return None, False

#######################################################################################################

class BasePackage(object):
	def __init__(self, name, bucket):
		self.name = name
		self.bucket = bucket
		self.actions = None

	def get_property(self, name):
		return self.bucket.get_property(name)
		
	def get_definition_location(self):
		#return self.bucket.file
		return self.bucket.abspath

	def get_install_path(self, workspace):
		#returns complete path (including the name)
		return os.path.join(workspace, self.name)

	def get_install_parent_folder(self, workspace):
		#returns folder where it's going to be installed
		return workspace

	#######################################################################################################

	def deserialize(self, params):
		if isinstance(params, str):
			return self.init_from_string(params)
		elif isinstance(params, dict):
			return self.init_from_dict(params)

		return False

	def init_from_string(self, params):
		return False

	def init_from_dict(self, params):
		return False

	def sanitize(self, workspace, fast):
		pass

	#######################################################################################################

	def get_status(self, fast):
		#TODO: cleanup
		#return wpm_internal_utils.PackageStatusMessage
		return None	

	def install(self, workspace):
		#returns True/False if install was successfull
		raise Exception("Missing install implementation!")

	def update(self, workspace):
		#returns True/False if update is sucessfull, 
		raise Exception("Missing update implementation!")

	def get_installed_revision(self, workspace):
		#returns sha 256 revision
		return None

	def get_remote_revision(self, branch):
		#returns sha 256 revision
		return None

	def get_actions(self, workspace):
		if self.actions != None:
			return self.actions

		afile = os.path.join(self.get_install_path(workspace), "actions.py")
		if not os.path.exists(afile):
			return None

		self.actions = PackageActions(f"{self.name}Actions", afile)
		return self.actions

	def format_string(self, s):
		return self.bucket.format_string_for_bucket(s)

#######################################################################################################
#######################################################################################################
#######################################################################################################

def _get_git_utils():
	from . import wpm_git_utils
	return wpm_git_utils

class GitEntry(BasePackage):
	ClassName = "git"
	def get_classname(self):
		return GitEntry.ClassName

	def __init__(self, name, bucket):
		BasePackage.__init__(self, name, bucket)
		
		self.model = wpm_package_models.GitModel()

	#######################################################################################################

	def init_from_dict(self, params):
		self.model.load_defaults(self.bucket)

		try:
			self.model.load_from_dict(params)
		except:
			return False

		return True

	def init_from_string(self, params):

		self.model.url = params
		self.model.active_branch = "master"

		self.model.load_defaults(self.bucket)
		return True

	#######################################################################################################

	def branch(self, branchname):
		self.model.active_branch = branchname

		return self

	def freeze(self, rev):
		self.model.locked = rev

		return self

	def user_name(self, name):
		self.model.username = name

		return self

	def user_email(self, email):
		self.model.useremail = email
		return self

	#######################################################################################################

	def get_active_branch(self):
		return self.model.active_branch

	def get_clone_url(self):
		return self.format_string(self.model.url)

	def install(self, workspace):
		u = _get_git_utils()
		return u.install_git_entry(workspace, self)

	def update(self, workspace):
		u = _get_git_utils()
		return u.update_git_entry(workspace, self)


	def get_installed_revision(self, workspace):
		u = _get_git_utils()
		return u.get_installed_revision(workspace, self)

	def get_remote_revision(self, branch = None):
		u = _get_git_utils()
		if branch == None:
			branch = self.get_active_branch()
		return u.get_remote_revision(branch, self)

	def get_status(self, workspace, fast):
		ipath = self.get_install_path(workspace)

		git_path = os.path.join(ipath, ".git")
		if os.path.exists(git_path):
			u = _get_git_utils();
			return u.get_git_status(self.model, self.get_install_path(workspace), fast)
		else:
			status = wpm_internal_utils.PackageStatusMessage()
			status.marker = "?"
			status.status = "VIEW"
			if self.model.locked != None:
				status.info = "locked:" + self.model.locked
			return status

	def sanitize(self, workspace, fast):
		u = _get_git_utils()
		u.refresh_git(self, fast, workspace)

#######################################################################################################

class LocalEntry(BasePackage):
	ClassName = "local"
	def get_classname(self):
		return LocalEntry.ClassName

	def __init__(self, name, bucket):
		BasePackage.__init__(self, name, bucket)
		
	#######################################################################################################


	def init_from_dict(self, params):
		return True

	def init_from_string(self, params):
		return True

	def install(self, workspace):
		return True
			
	def get_status(self, workspace, fast):
		return wpm_internal_utils.PackageStatusMessage()

	def sanitize(self, workspace, fast):
		u = _get_git_utils()
		u.refresh_git(self, fast, workspace)

#######################################################################################################

class ZipEntry(BasePackage):
	ClassName = "zip"
	def get_classname(self):
		return ZipEntry.ClassName

	def __init__(self, name, bucket):
		BasePackage.__init__(self, name, bucket)
		self.url = None

	def init_from_dict(self, params):
		try:
			self.url = params["url"]
		except:
			return False

		return True

	def init_from_string(self, params):
		self.url = params
		return True

	def install(self, workspace):

		ifolder = self.get_install_parent_folder(workspace)
		if not os.path.exists(ifolder):
			os.makedirs(ifolder)

		cmd = ""
		cmd = cmd + f"cd {ifolder};"
		cmd = cmd + f"wget {self.url} -O {self.name}.zip;"
		cmd = cmd + f"unzip {self.name}.zip;"
		cmd = cmd + f"rm {self.name}.zip;"

		wpm_internal_utils.run_command_and_wait(cmd, workspace, True)
