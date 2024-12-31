
import os
import sys
import time
import shutil
import subprocess

def run_command_and_wait(cmd, _cwd, _shell=False):
	sys.stdout.flush()

	#print(cmd)

	e = subprocess.run(cmd, cwd = _cwd, capture_output=True, shell=_shell)
	stderr = e.stderr.decode("utf-8").strip()
	stdout = e.stdout.decode("utf-8").strip()

	if (stderr != ""):
		print("err: {")
		print("  >> " + stderr.replace("\n","\n  >> "))
		print("}")
	if (stdout != ""):
		print("out: {")
		print("     " + stdout.replace("\n","\n    "))
		print("}")
	sys.stdout.flush()
	return e.returncode

def run_command_in_active_terminal(cmd, _cwd):
	result = subprocess.run(cmd, cwd = _cwd, text=True)
	return e.returncode

def run_silent_command(cmd, _cwd):
	#p = subprocess.Popen([cmd], cwd = _cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
	p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=_cwd, text=True, shell=True)
	return p.stdout

def actually_remove_folder(path):
	if os.path.exists(path) == False:
		return
	
	sys.stdout.flush()
	shutil.rmtree(path)
	itr = 0
	while os.path.exists(path):
		if itr > 10:
			print("Error: Failed to remove [" + path + "]")
			sys.exit(-1)

		time.sleep(0.1)
		itr = itr + 1

class PackageStatusMessage():
	def __init__(self):
		self.marker = " "
		self.status = ""
		self.info = ""

		self.updatable = False


def compute_duration(start_time):
	end = time.time()
	duration = "{:.3f}".format(end - start_time) + " sec"
	return duration

class Colors:
	""" ANSI color codes """
	BLACK = "\033[0;30m"
	RED = "\033[0;31m"
	GREEN = "\033[0;32m"
	BROWN = "\033[0;33m"
	BLUE = "\033[0;34m"
	PURPLE = "\033[0;35m"
	CYAN = "\033[0;36m"
	LIGHT_GRAY = "\033[0;37m"
	DARK_GRAY = "\033[1;30m"
	LIGHT_RED = "\033[1;31m"
	LIGHT_GREEN = "\033[1;32m"
	YELLOW = "\033[1;33m"
	LIGHT_BLUE = "\033[1;34m"
	LIGHT_PURPLE = "\033[1;35m"
	LIGHT_CYAN = "\033[1;36m"
	LIGHT_WHITE = "\033[1;37m"
	BOLD = "\033[1m"
	FAINT = "\033[2m"
	ITALIC = "\033[3m"
	UNDERLINE = "\033[4m"
	BLINK = "\033[5m"
	NEGATIVE = "\033[7m"
	CROSSED = "\033[9m"
	END = "\033[0m"
	
	# cancel SGR codes if we don't write to a terminal
	if not __import__("sys").stdout.isatty():
		for _ in dir():
			if isinstance(_, str) and _[0] != "_":
				locals()[_] = ""
	else:
		# set Windows console in VT mode
		if __import__("platform").system() == "Windows":
			kernel32 = __import__("ctypes").windll.kernel32
			kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
			del kernel32


def LineSize():
	try:
		terminal_size = os.get_terminal_size()
		columns = terminal_size.columns
	except OSError:
		columns = 80
	
	# Print dashes across the current line
	return columns