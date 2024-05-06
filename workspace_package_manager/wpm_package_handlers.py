
import os
import sys
import json
import requests
import zipfile
import io
import shutil
import importlib.util

from . import wpm_package_models
from . import wpm_internal_utils

class BucketDefinition():
	def __init__(self, parent, abs_path):
		self.parent = parent
		self.folder, self.file = os.path.split(abs_path)
		self.abspath = abs_path
		self.props = None
		self.rprops = None
		
	def get_property(self, name):
		if self.props != None:
			return self.props.get(name, None)
		if self.parent != None:
			return self.parent.get_property(name)
		return None

	def set_property(self, pname, pvalue):
		if self.props == None:
			self.props = {}

		self.props[pname] = str(pvalue)

	#def get_all(self):
	#	if self.props != None:
	#		return self.props
    #
	#	return {}

	def get_recursive_properties(self):
		props = {}
		if self.parent != None:
			props.update(self.parent.get_recursive_properties())

		if self.props != None:
			props.update(self.props)

		return props

	def format_string(self, s):
		if self.props != None:
			try:
				return s.format(**self.props)
			except KeyError:
				pass
		return s

	def load_json_properties(self, jdict):
		self.props = jdict

	def get_flat_properties(self, database):
		rp = self.get_recursive_properties()
		rp.update(database.fetch_properties([k for k in rp.keys()]))
		return rp


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

class BasePackage(object):
	def __init__(self, name, pdatabase, bucket):
		self.name = name
		self.database = pdatabase
		self.bucket = bucket
		self.actions = None

	def get_property(self, name):
		return self.bucket.get_property(name)
		
	def get_definition_location(self):
		return self.bucket.file

	def deserialize(self, params):
		if isinstance(params, str):
			return self.init_from_string(params)
		elif isinstance(params, dict):
			return self.init_from_dict(params)

		return False

	def get_install_path(self, workspace):
		#returns complete path (including the name)
		return os.path.join(workspace, self.name)

	def get_install_parent_folder(self, workspace):
		#returns folder where it's going to be installed
		return workspace

	#######################################################################################################

	def init_from_string(self, params):
		return False

	def init_from_dict(self, params):
		return False

	def sanitize(self, workspace, fast):
		pass

	def get_status(self, fast):
		return None	

	def get_update_command(self):
		return None

	def install(self, workspace):
		#returns True/False if install was successfull
		return False

	def generate_install_command(self, workspace):
		#returns a command which can be pasted into the terminal to install the package somewhere
		pass

	def get_actions(self, workspace):
		if self.actions != None:
			return self.actions

		afile = os.path.join(self.get_install_path(workspace), "actions.py")
		if not os.path.exists(afile):
			return None

		self.actions = PackageActions(f"{self.name}Actions", afile)
		return self.actions

	def format_string(self, s):
		
		props = self.bucket.get_flat_properties(self.database)		
		
		try:
			return s.format(**props)
		except KeyError as e:
			raise Exception(f"Missing key in string {s}:{e}")


#######################################################################################################
def _get_git_utils():
	from . import wpm_git_utils
	return wpm_git_utils

class GitEntry(BasePackage):
	def __init__(self, name, pakdb, definition):
		BasePackage.__init__(self, name, pakdb, definition)
		
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
		return u.install_git_entry(workspace, self);
			
	def generate_install_command(self):
		u = _get_git_utils()
		url = self.get_clone_url()
		return u.create_install_command(
			url,
			self.model,
			self.name
		)

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
			

	def get_update_command(self):
		return self.name

	def sanitize(self, workspace, fast):
		u = _get_git_utils()
		u.refresh_git(self, fast, workspace)

		

#######################################################################################################

class ZipEntry(BasePackage):
	def __init__(self, name, pakdb, definition):
		BasePackage.__init__(self, name, pakdb, definition)
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
