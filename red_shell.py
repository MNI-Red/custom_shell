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

def clean_processes(pid_to_process, pid_to_command):
	to_remove = []
	for pid in pid_to_process:
		if pid_to_process[pid].poll() != None:
			to_remove.append(pid)
	[pid_to_process.pop(proc) for proc in to_remove]
	[pid_to_command.pop(proc) for proc in to_remove]

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

# def fg_bg()

# def run_process(command_line):
# 	p = sbp.Popen(command_line)
# 	return p, pid

def loop():
	cwd = os.getcwd()
	# past_commands = set()
	pid_to_process= {}
	pid_to_command = {}
	signal.signal(signal.SIGTSTP, create_handler(pid_to_process, signal.SIGTSTP))
	signal.signal(signal.SIGINT, create_handler(pid_to_process, signal.SIGINT))
	

	while True:
		clean_processes(pid_to_process, pid_to_command)
		print(pid_to_process)
		# try:
		command_line, background, original = get_input()
		# past_commands.add(command_line)
		if len(command_line) < 1:
			continue
		command = command_line[0]
		if command == "exit":
			for i in pid_to_process:
				pid_to_process[i].kill()
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
			if len(pid_to_command) > 0:
				print()
				for pid in pid_to_command:
					# print(proc.args)
					print("PID: " + str(pid) + ") " + pid_to_command[pid])
				print()
		elif command == "fg":
			if len(command_line) < 2 or not command_line[1].isdecimal():
				print("Please enter PID of process to foreground")
				continue
			pid = int(command_line[1])
			# print(pid)
			# print(list(pid_to_process.keys()))
			# print(pid in list(pid_to_process.keys()))
			if pid not in list(pid_to_process.keys()):
				print("Please enter the PID of an existing process. Find the PIDs by using the \'jobs\' command.")
				continue
			arguments = pid_to_process[pid].args
			pid_to_process[pid].send_signal(signal.SIGCONT)
			p = sbp.Popen(arguments[:-1])
			pid_to_process[p.pid] = p
			pid_to_command[p.pid] = original
		elif command == "bg":
			if len(command_line) < 2 or not command_line[1].isdecimal():
				print("Please enter PID of process to foreground")
				continue
			pid = int(command_line[1])
			if pid not in list(pid_to_process.keys()):
				print("Please enter the PID of an existing process. Find the PIDs by using the \'jobs\' command.")
				continue
			arguments = pid_to_process[pid].args
			arguments.append('&')
			pid_to_process[pid].send_signal(signal.SIGCONT)
			p = sbp.Popen(arguments[:])
			pid_to_process[p.pid] = p
			pid_to_command[p.pid] = original
		else:
			# if not background:
			try:
				p = sbp.Popen(command_line)
				pid_to_process[p.pid] = p
				pid_to_command[p.pid] = original
				# processes[p.pid] = [p, original]
				if not background:
					p.communicate()
				# else:
				# 	p = sbp.Popen(command_line, shell=True,
	#          stdin=None, stdout=None, stderr=None, close_fds=True)
				# 	p.wait()
				print(p.pid)
				# p.communicate()
				# print(out)
			except PermissionError:
				print("Permission Error: not a binary command or builtin or one you do not have acces to.")
				continue
		# except KeyboardInterrupt:
		# 	continue

loop()