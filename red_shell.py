import os
import getpass
import sys
import signal
import shlex
import pipes
import threading
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

def clean_pipe(pid_to_process, pid_to_command, key):
	processes = pid_to_process[key]
	to_remove = []
	for i in processes:
		if i.poll() != None:
			to_remove.append(i.pid)
	new_key = tuple([i for i in key if i not in to_remove])
	pid_to_process.pop(key)
	command = pid_to_command.pop(key)
	if len(new_key) > 1:
		pid_to_process[new_key] = processes[:-len(new_key)]
		pid_to_command[new_key] = command


def clean_processes(pid_to_process, pid_to_command):
	to_remove = []
	pipe_ids = []
	for pid in pid_to_process:
		if type(pid) is tuple:
			pipe_ids.append(pid)
			continue
		if pid_to_process[pid].poll() != None:
			to_remove.append(pid)
	[pid_to_process.pop(proc) for proc in to_remove]
	[pid_to_command.pop(proc) for proc in to_remove]
	for i in pipe_ids:
		clean_pipe(pid_to_process, pid_to_command, i)

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

def pipe(commands_to_pipe):
	first, last = commands_to_pipe[0], commands_to_pipe[-1]
	process = sbp.Popen(first, stdout=sbp.PIPE)
	pid_list = [process.pid]
	process_list = [process]
	out = process.stdout

	for command in commands_to_pipe[1:-2]:
		previous = process
		process = sbp.Popen(command, stdin=out, stdout=sbp.PIPE)
		out = process.stdout
		previous.stdout.close()
		pid_list.append(process.pid)
		process_list.append(process)
		

	process = sbp.Popen(last, stdin=out)
	pid_list.append(process.pid)
	# print(pid_list)
	full_pid = tuple(pid_list)
	# pid_to_process[full_pid] = " | ".join(process_list)
	# pid_to_command[full_pid] = original

	return pid_list, full_pid, process_list
	
def pipe_wait(process_list):
	results = [0]*len(process_list)
	while process_list:
		last = process_list.pop(-1)
		results[len(process_list)] = last.wait()
	return results


def parse_subcommands(command_line):
	stack = []
	commands = []
	# to_remove = ["$(", ")"]
	for i in command_line:
		if '$(' in i:
			stack.extend(["$(", i[2:]])
		elif ")" in i:
			stack.extend([i[:-i.count(')')]]+[')']*i.count(')'))
		else:
			stack.append(i)
	print(stack)
	while ')' in stack:
		stack.pop(-1)
	print(stack)
	while '$(' in stack:
		last_dollar = stack[::-1].index('$(')
		commands.append(stack[-last_dollar:])
		stack = stack[:-last_dollar-1]
	commands.extend(stack)
	# print(commands)
	# commands.reverse()
	return commands

def execute_command(command, command_line, original, background, piping, in_redirect, out_redirect, pid_to_process, 
	pid_to_command):
	if command == "exit":
		for i in pid_to_process:
			if type(i) is tuple:
				for process in pid_to_process[i]:
					process.kill()
				continue
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
			# break
		except IndexError as i:
			print("Please enter a directory to switch to.")
			# break
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
			return
		pid = int(command_line[1])
		# print(pid)
		# print(list(pid_to_process.keys()))
		# print(pid in list(pid_to_process.keys()))
		if pid not in list(pid_to_process.keys()):
			print("Please enter the PID of an existing process. Find the PIDs by using the \'jobs\' command.")
			return
		arguments = pid_to_process[pid].args
		pid_to_process[pid].send_signal(signal.SIGCONT)
		p = sbp.Popen(arguments[:-1])
		pid_to_process[p.pid] = p
		pid_to_command[p.pid] = original
	elif command == "bg":
		if len(command_line) < 2 or not command_line[1].isdecimal():
			print("Please enter PID of process to foreground")
			return
		pid = int(command_line[1])
		if pid not in list(pid_to_process.keys()):
			print("Please enter the PID of an existing process. Find the PIDs by using the \'jobs\' command.")
			return
		arguments = pid_to_process[pid].args
		arguments.append('&')
		pid_to_process[pid].send_signal(signal.SIGCONT)
		p = sbp.Popen(arguments[:])
		pid_to_process[p.pid] = p
		pid_to_command[p.pid] = original
	else:
		# if not background:
		try:
			if piping:
				pid_list, full_pid, process_list = pipe(commands_to_pipe)
				pid_to_process[full_pid] = process_list
				pid_to_command[full_pid] = original

				if not background:
					# print("not background")
					# result_available = threading.Event()
					# thread = threading.Thread(target=pipe_wait, args=((process_list,)))
					# thread.start()
					# thread.join()
					# pipe_wait(process_list)
					# print("x,y,z")
					print(process_list[-1].communicate()[0].decode("utf-8"))
					# process_list[-1].stdout.flush()
			else:
				p = sbp.Popen(command_line, stdin=in_redirect, stdout=out_redirect, stderr=sbp.STDOUT)
				pid_to_process[p.pid] = p
				pid_to_command[p.pid] = original
				# processes[p.pid] = [p, original]
				if not background:
					p.communicate()
				# else:
				# 	python -m SimpleHTTPServer 8080 &
				# 	p = sbp.Popen(command_line, shell=True,
				#stdin=None, stdout=None, stderr=None, close_fds=True)
				# 	p.wait()
				# print(p.pid)
				# p.communicate()
				# print(out)
		except PermissionError:
			print("Permission Error: not a binary command or builtin or one you do not have acces to.")
			return

def loop():
	cwd = os.getcwd()
	# past_commands = set()
	pid_to_process= {}
	pid_to_command = {}
	signal.signal(signal.SIGTSTP, create_handler(pid_to_process, signal.SIGTSTP))
	signal.signal(signal.SIGINT, create_handler(pid_to_process, signal.SIGINT))
	# signal.signal(signal.SIGPIPE, signal.SIG_DFL)
	while True:
		clean_processes(pid_to_process, pid_to_command)
		# print(pid_to_process)
		# try:
		piping = False
		cheat_shell = False
		subcommands = False
		in_redirect = None
		out_redirect = None

		command_line, background, original = get_input()
		print(command_line)
		
		if "|" in command_line:
			# find /home/dros -name "*.txt" | sort -n | uniq | cat
			piping = True
			new_split = [l.split(' ') for l in ' '.join(command_line).split("|")]
			commands_to_pipe = [new_split[0][0]] + [l[1] for l in new_split[1:-1]] + [new_split[-1][-1]]
			# print(new_split)
			# print(commands_to_pipe)
		if "<" in command_line:
			# new_split = [command_line[:command_line.index("<")]]
			index = command_line.index("<")
			file_name = command_line[index+1:][0]
			command_line = command_line[:index]
			# file_name = new_split[1][1]
			# print(command_line, file_name)
			try:
				in_redirect = open(file_name, 'r')
			except FileNotFoundError:
				print(file_name + ": no such file or directory")
				continue
		elif ">" in command_line:
			index = command_line.index(">")
			file_name = command_line[index+1:][0]
			command_line = command_line[:index]
			# print(command_line, file_name)
			out_redirect = open(file_name, "w")

		if any(["$" in i for i in command_line]):
			commands_to_pipe = parse_subcommands(command_line)
			piping = True


		if len(command_line) < 1:
			continue
		
		command = command_line[0]
		if command == "exit":
			for i in pid_to_process:
				if type(i) is tuple:
					for process in pid_to_process[i]:
						process.kill()
					continue
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
				if piping:
					pid_list, full_pid, process_list = pipe(commands_to_pipe)
					pid_to_process[full_pid] = process_list
					pid_to_command[full_pid] = original

					if not background:
						# print("not background")
						# result_available = threading.Event()
						# thread = threading.Thread(target=pipe_wait, args=((process_list,)))
						# thread.start()
						# thread.join()
						# pipe_wait(process_list)
						# print("x,y,z")
						print(process_list[-1].communicate()[0].decode("utf-8"))
						# process_list[-1].stdout.flush()
				# elif subcommands:
				# 	# print(parsed_command_list)
				# 	pid_list = []
				# 	process_list = []
				# 	first = parsed_command_list.pop(-1)
				# 	p = sbp.Popen(first, stdin=in_redirect, stdout=out_redirect, stderr=sbp.STDOUT)
				# 	pid_list.append(p.pid)
				# 	process_list.append(first)
				# 	args = [p.communicate()]
				# 	print(args)
				# 	while parsed_command_list:
				# 		current = [parsed_command_list.pop(-1)]
				# 		# print(current+args)
				# 		p = sbp.Popen(current+args, stdin=in_redirect, stdout=out_redirect, stderr=sbp.STDOUT)
				# 		pid_list.append(p.pid)
				# 		process_list.append(current)
				# 		args = [p.communicate()]
				# 	pid_to_process[tuple(pid_list)] = process_list
				# 	pid_to_command[tuple(pid_list)] = original


				else:
					p = sbp.Popen(command_line, stdin=in_redirect, stdout=out_redirect, stderr=sbp.STDOUT)
					pid_to_process[p.pid] = p
					pid_to_command[p.pid] = original
					# processes[p.pid] = [p, original]
					if not background:
						p.communicate()
					# else:
					# 	python -m SimpleHTTPServer 8080 &
					# 	p = sbp.Popen(command_line, shell=True,
					#stdin=None, stdout=None, stderr=None, close_fds=True)
					# 	p.wait()
					# print(p.pid)
					# p.communicate()
					# print(out)
			except PermissionError:
				print("Permission Error: not a binary command or builtin or one you do not have acces to.")
				continue
		# except KeyboardInterrupt:
		# 	continue

loop()