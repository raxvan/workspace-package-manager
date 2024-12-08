
import os
import io
import sys
import json
import hashlib
import requests
import zipfile
import time
import shutil

from . import wpm_internal_utils
from . import wpm_package_handlers

_colors = wpm_internal_utils.Colors

class PackageDatabaseConstructor(object):
	def __init__(self, package_database, logger):
		self.database = package_database

		self.active_bucket = None
		self.item_stack = []
		self.logger = logger

	def add_bucket(self, rel_path_to_dir):
		active_folder = self.active_bucket.folder
		abs_path = os.path.join(active_folder, rel_path_to_dir);
		self.load_bucket(abs_path)

	def add_github_bucket(self, property_check, name, github_path, install_path = None):
		
		ipath = None
		if install_path != None:
			if os.path.isabs(install_path):
				ipath = install_path 
			else:
				ipath = os.path.join(os.path.join(self.active_bucket.folder, install_path))
		else:
			ipath = self.active_bucket.folder
		
		abspath = os.path.join(ipath, name)
		
		if not os.path.exists(abspath):
			if property_check != None and self.active_bucket.has_property(property_check):
				if self.logger != None:
					self.logger(f"   {_colors.YELLOW}!ignoring {_colors.CYAN}{name}{_colors.YELLOW} due to {property_check} missing ...{_colors.END}")
				return
			else:
				if self.logger != None:
					self.logger(f"   {_colors.RED}+ fetching {name} -> {ipath} {_colors.END}")
				e = self.add_git(name, github_path).branch("main")	
				e.install(ipath)

		self.add_bucket(abspath)

	def load_bucket_list(self, workspace, bucket_list):
		start = time.time()
		
		if self.logger != None:
			self.logger(f"{_colors.LIGHT_BLUE}-- workspace:{_colors.END} {_colors.PURPLE}{workspace}{_colors.END}")
			self.logger(f"{_colors.LIGHT_BLUE}-- loading packages:{_colors.END}")

		#main definition in this repo
		for b in bucket_list:
			if os.path.exists(b):
				self.load_bucket(b)
		
		if self.logger != None:
			duration = wpm_internal_utils.compute_duration(start)
			self.logger(f"{_colors.LIGHT_GREEN}-- {_colors.BOLD}OK{_colors.END} {_colors.DARK_GRAY}({duration}){_colors.END}")
			self.logger(_colors.DARK_GRAY + "-" * 64 + _colors.END)

	def add_git(self, package_name, params):
		entry = wpm_package_handlers.GitEntry(package_name, self.active_bucket)

		if entry.deserialize(params) == False:
			return None

		self.database.add_package(package_name, entry)

		return entry

	def add_zip(self, package_name, params):
		entry = wpm_package_handlers.ZipEntry(package_name, self.active_bucket)

		return self._add_entry(entry, params)

	def add_entry(self, package_name, serialized_entry):
		_class = serialized_entry.get("class", None)
		entry = self.create_entry(_class, package_name)
		if entry == None:
			return None
		
		return self._add_entry(entry, serialized_entry)

	def set(self, pname, pvalue = ""):
		self.active_bucket.set_property(pname, pvalue);

	def _add_entry(self, entry, contents):
		if entry.deserialize(contents) == False:
			if self.logger != None:
				self.logger(f"{_colors.LIGHT_RED}WARNING: Failed to deserialize entry {entry.name} ...{_colors.END}")
			return None

		self.database.add_package(entry.name, entry)
		return entry

	def create_entry(self, classname, package_name):
		if classname == wpm_package_handlers.GitEntry.ClassName:
			return wpm_package_handlers.GitEntry(package_name, self.active_bucket)
		elif classname == wpm_package_handlers.LocalEntry.ClassName:
			return wpm_package_handlers.LocalEntry(package_name, self.active_bucket)
		elif classname == wpm_package_handlers.ZipEntry.ClassName:
			return wpm_package_handlers.ZipEntry(package_name, self.active_bucket)
		else:
			if self.logger != None:
				self.logger(f"{_colors.LIGHT_RED}WARNING: Failed to create entry with class '{classname}' ...{_colors.END}")

		return None

	#######################################################################################################
	#######################################################################################################
	#######################################################################################################

	def _push_definition(self, abs_item_path):
		if not os.path.exists(abs_item_path):
			return False

		if self.database.add_definition(abs_item_path) == False:
			return False

		self.active_bucket = wpm_package_handlers.BucketDefinition(self.active_bucket, self.database, abs_item_path)
		self.item_stack.append(self.active_bucket)

		return True

	def _pop_definition(self, abs_item_path):
		self.item_stack.pop()
		if self.item_stack:
			self.active_bucket = self.item_stack[-1]
		else:
			self.active_bucket = None

	#######################################################################################################
	#######################################################################################################
	def _load_json_content(self, content):
		bdata = content.get(".bucket", None)
		if bdata != None:
			self.active_bucket.load_json_properties(bdata)

		for k,v in content.items():
			if k.startswith("."):
				continue
			self.add_entry(k, v)

	def load_json(self, abs_path_to_file):
		if self._push_definition(abs_path_to_file) == False:
			return False

		active_folder = self.active_bucket.folder
		if self.logger != None:
			self.logger(f"     {_colors.CYAN}{os.path.relpath(abs_path_to_file, active_folder)}{_colors.END}")

		json_content = None	
		try:
			f = open(abs_path_to_file,"r")
			json_content = json.load(f)
			f.close()
		except:
			raise Exception(f"Invalid json {abs_path_to_file}\n")

		self._load_json_content(json_content)

		self._pop_definition(abs_path_to_file)

		return True

	#def load_encrypted_json(self, abs_path_to_file):
	#
	#	if self._push_definition(abs_path_to_file) == False:
	#		return False
	#
	#	active_folder = self.active_bucket.folder
	#	if self.logger != None:
	#		self.logger(f"     {_colors.CYAN}{os.path.relpath(abs_path_to_file, active_folder)}{_colors.END}")
	#
	#	active_file = self.active_bucket.file
	#	file_secret = self.database.vault[active_file]
	#	if file_secret == None:
	#		return False
	#
	#	json_content = secretsvault.vault_decode_file(file_secret, abs_path_to_file, None)
	#
	#	try:
	#		json_content = json.loads(json_content)
	#	except:
	#		raise Exception(f"Invalid json {abs_path_to_file}\n")
	#
	#	self._load_json_content(json_content)
	#
	#	self._pop_definition(abs_path_to_file)
	#	return True
	
	def load_constructor(self, abs_path_to_file):
		if self._push_definition(abs_path_to_file) == False:
			return False

		active_folder = self.active_bucket.folder
		if self.logger != None:
			self.logger(f"     {_colors.CYAN}{os.path.relpath(abs_path_to_file, active_folder)}{_colors.END}")

		import importlib.util
		load_location = "definition.sha" + hashlib.sha256(abs_path_to_file.encode('utf-8')).hexdigest()
		spec = importlib.util.spec_from_file_location(load_location, abs_path_to_file)
		constructor = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(constructor)

		constructor.load(self)

		self._pop_definition(abs_path_to_file)
		return True

	#######################################################################################################

	def _bucket_ignore(self, abs_path_to_dir, abs_item_path, item_name):
		
		if item_name.startswith("."):
			return True

		#hack to bypass stupid mac files
		#if str(item_name).startswith("._") and os.path.exists(os.path.join(abs_path_to_dir, str(p)[2:])):
		#	return True

		if item_name == "__pycache__":
			return True

		return False

	def _load_item(self, abs_item_path):
		loaded = False
		if abs_item_path.endswith(".json"):
			loaded = self.load_json(abs_item_path)
		elif abs_item_path.endswith(".py"):
			loaded = self.load_constructor(abs_item_path)
		#elif abs_item_path.endswith(".ejson"):
		#	loaded = self.load_encrypted_json(abs_item_path)
		else:
			#silent skip
			return
		
		if loaded == False and self.logger != None:
			self.logger(f"{_colors.YELLOW}   ! {abs_item_path} skipped ...{_colors.END}")


	def load_bucket(self, abs_path_to_dir):
		if self._push_definition(abs_path_to_dir) == False:
			return False

		folders_and_files = os.listdir(abs_path_to_dir)

		if self.logger != None:
			self.logger(f"   {_colors.BROWN}#{abs_path_to_dir}{_colors.END}")

		for i in folders_and_files:
			abs_item_path = os.path.join(abs_path_to_dir, i)

			if self._bucket_ignore(abs_path_to_dir, abs_item_path, i):
				continue

			self._load_item(abs_item_path)

		self._pop_definition(abs_path_to_dir)
		return True


#######################################################################################################
#######################################################################################################
#######################################################################################################
#######################################################################################################

class PackageDatabase(object):
	def __init__(self):
		
		self.db = {}
		self.modules = set()

		self.properties = {}

	def load_workspace(self, workspace):

		config_path = os.path.join(workspace, ".wpm", "config.json")
		try:
			if os.path.exists(config_path):
				with open(config_path, "r") as f:
					self.properties.update(json.load(f))

		except Exception as e:
			raise Exception(f"{_colors.RED}[ERROR]{_colors.END} Failed to load config {config_path}\n{e}")

	def get_all_names(self):
		return [x for x,_ in self.db.items()]

	def get(self, name):
		return self.db[name]

	def getall(self):
		return self.db.items()

	def find(self, name):
		return self.db.get(name, None)

	def get_all_properties(self):
		return self.properties

	def has_property(self, pname):
		if pname in self.properties:
			return True
		return False

	def fetch_properties(self, proplist):
		if self.decoder != None:
			return self.decoder.query(proplist)

	#######################################################################################################
	#######################################################################################################

	def add_package(self, package_name, newp):
		pp = self.db.get(package_name, None)
		if pp != None:
			m = f"Duplicate package found: {package_name}\n"
			m += f"\t -> {pp.get_definition_location()}\n"
			m += f"\t -> {newp.get_definition_location()}\n"
			raise Exception(m)

		self.db[package_name] = newp

	def add_definition(self, abs_def_path):
		if abs_def_path in self.modules:
			return False

		self.modules.add(abs_def_path)
		return True

	#######################################################################################################
