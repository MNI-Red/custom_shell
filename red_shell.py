import os
import getpass
import sys
import signal
import shlex
import subprocess as sbp
# print(getpass.getuser())

def get_input():
	background = False
	command_line = input(str(getpass.getuser()) + " " + str(os.getcwd()) + " > ")
	# print(command_line)
	if '&' in command_line:
		# command_line = command_line[:-1]
		background = True
	return shlex.split(command_line), background, command_line

def clean_processes(processes):
	to_remove = []
	for proc in processes:
		if proc.poll() != None:
			to_remove.append(proc)
	[processes.pop(proc) for proc in to_remove]

def create_handler(obj, signal):
	def _handler(signum, frame):
		try:
			obj[-1].send_signal(signal)
		except KeyError:
			pass
	return _handler

def sigint(obj):
	def _handler(signum, frame):
		try:
			obj[-1].send_signal(signum)
		except KeyError:
			pass
	return _handler

def sigint(signum, frame):
    processes[-1].kill()

def loop():
	cwd = os.getcwd()
	# past_commands = set()
	processes = {}
	signal.signal(signal.SIGTSTP, create_handler(processes, signal.SIGTSTP))
	signal.signal(signal.SIGINT, create_handler(processes, signal.SIGINT))
	

	while True:
		clean_processes(processes)
		print(processes)
		# try:
		command_line, background, original = get_input()
		# past_commands.add(command_line)
		command = command_line[0]
		if command == "exit":
			for i in processes:
				i.kill()
			sys.exit()
		elif command == "pwd":
			print(cwd)
		elif command == "cd":
			try:
				os.chdir(command_line[1])
				cwd = os.getcwd()
			except FileNotFoundError as e:
				print(e)
				continue
			except IndexError as i:
				print("Please enter a directory to switch to.")
				continue
		elif command == "jobs":
			if len(processes) > 0:
				print()
				for proc in processes:
					# print(proc.args)
					print("PID: " + str(processes[proc][0]) + ") " + processes[proc][1])
				print()
		else:
			# if not background:
			p = sbp.Popen(command_line)
			processes[p] = [p.pid, original]
			if not background:
				p.communicate()
			# else:
			# 	p = sbp.Popen(command_line, shell=True,
#          stdin=None, stdout=None, stderr=None, close_fds=True)
			# 	p.wait()
			print(p.pid)
			# p.communicate()
			# print(out)
		# except KeyboardInterrupt:
		# 	continue

loop()