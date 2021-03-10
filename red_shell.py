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

def pipe(commands_to_pipe, first_in, last_out):
	first, last = commands_to_pipe[0], commands_to_pipe[-1]
	process = sbp.Popen(first, stdin = first_in, stdout=sbp.PIPE)
	pid_list = [process.pid]
	process_list = [process]
	out = process.stdout

	for command in commands_to_pipe[1:-1]:
		previous = process

		process = sbp.Popen(command, stdin=out, stdout=sbp.PIPE)
		out = process.stdout

		previous.stdout.close()

		pid_list.append(process.pid)
		process_list.append(process)
		
	process = sbp.Popen(last, stdin=out, stdout=last_out)
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
	# print(stack)
	while ')' in stack:
		stack.pop(-1)
	# print(stack)
	while '$(' in stack:
		last_dollar = stack[::-1].index('$(')
		commands.append(stack[-last_dollar:])
		stack = stack[:-last_dollar-1]
	commands.extend(stack)
	# print(commands)
	# commands.reverse()
	return commands

def subcommand_chain(commands, first_in, last_out):
	# print(commands)
	process = sbp.Popen(commands[0], stdin=first_in, stdout=sbp.PIPE)
	pid_list = [process.pid]
	process_list = [process]
	args = [process.communicate()[0].decode("utf-8")]
	# print()
	for i in commands[1:-1]:
		previous = process
		if type(i) is not list:
			i = [i]
		i.extend(args)
		# print(i)
		# echo $(seq 1 10)
		process = sbp.Popen(i, stdout=sbp.PIPE)
		pid_list.append(process.pid)
		process_list.append(process)
		args = process.stdout
		previous.stdout.close()
		# print(args)
	
	last = commands[-1]
	if type(last) is not list:
			last = [last]
	last.extend(args)
	process = sbp.Popen(last, stdout=last_out)
	pid_list.append(process.pid)
	process_list.append(process)
	# args = process.communicate()[0].decode("utf-8")
	return pid_list, tuple(pid_list), process_list

def subcommand_and_pipe(commands, first_in, last_out):
	pid_list = []
	process_list = []
	first, last = commands[0], commands[-1]
	# print(commands) 
	# print(commands[1:-1])
	if any(["$" in i for i in first]):
		to_run = parse_subcommands(first)
		print(to_run)
		temp_pid_list, temp_full_pid, temp_process_list = subcommand_chain(to_run, first_in, sbp.PIPE)
		pid_list.extend(temp_pid_list)
		process_list.extend(temp_process_list)
		process = process_list[-1]
	else:
		process = sbp.Popen(first, stdin = first_in, stdout=sbp.PIPE)
		pid_list.append(process.pid)
		process_list.append(process)

	out = process.stdout
	# print(out.read())
	# print(process.communicate()[0])
	for proc in commands[1:-1]:
		previous = process
		# print(proc)
		if any(["$" in i for i in proc]):
			to_run = parse_subcommands(proc)
			temp_pid_list, temp_full_pid, temp_process_list = subcommand_chain(to_run, out, sbp.PIPE)
			pid_list.extend(temp_pid_list)
			process_list.extend(temp_process_list)
			process = process_list[-1]
		else:
			process = sbp.Popen(proc, stdin=out, stdout=sbp.PIPE)
			pid_list.append(process.pid)
			process_list.append(process)

		out = process.stdout
		previous.stdout.close()
		# print(out.read())

	if any(["$" in i for i in last]):
		to_run = parse_subcommands(last)
		print(to_run)
		temp_pid_list, temp_full_pid, temp_process_list = subcommand_chain(to_run, out, last_out)
		pid_list.extend(temp_pid_list)
		process_list.extend(temp_process_list)
		process = process_list[-1]
	else:
		process = sbp.Popen(last, stdin = out, stdout=last_out)
		pid_list.append(process.pid)
		process_list.append(process)

	return pid_list, tuple(pid_list), process_list

def echo_PID_to_user(pid, original):
	print("PID: " + str(pid) + ") " + original)

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
		piping, subcommands = False, False
		in_redirect, out_redirect, first_in, last_out = None, None, None, None
		command_line, background, original = get_input()
		# commands_to_run = command_line[:]
		# print("Initial parse: " + str(command_line))
		
		piping = "|" in command_line
		subcommands = any(["$" in i for i in command_line])
		if piping and subcommands:
			# echo $(echo $(echo $(echo $(seq 1 10)))) | cat
			new_split = [l.split(' ') for l in ' '.join(command_line).split("|")]
			print(new_split)
			command_line = [new_split[0][:-1]] + [l[1:-1] for l in new_split[1:-1]] + [new_split[-1][1:]]

			# command_line = parse_subcommands(command_line)
			print(command_line)
			last_out = sbp.PIPE
		elif piping:
			# find /home/dros -name "*.txt" | sort -n | uniq | cat
			new_split = [l.split(' ') for l in ' '.join(command_line).split("|")]
			print(new_split)
			commands_to_pipe = [new_split[0][:-1]] + [l[1:-1] for l in new_split[1:-1]] + [new_split[-1][1:]]
			# commands_to_run = commands_to_pipe
			# print(new_split)
			# print(commands_to_pipe)
			last_out = sbp.PIPE
		elif subcommands:
			command_line = parse_subcommands(command_line)
			last_out = sbp.PIPE
		
		# print(commands_to_pipe)
		# print(command_line)
		if "<" in command_line:
			# new_split = [command_line[:command_line.index("<")]]
			index = command_line.index("<")
			file_name = command_line[index+1:][0]
			command_line = command_line[:index]
			# file_name = new_split[1][1]
			# print(command_line, file_name)
			try:
				first_in = open(file_name, 'r')
			except FileNotFoundError:
				print(file_name + ": no such file or directory")
				continue
		elif ">" in command_line:
			index = command_line.index(">")
			file_name = command_line[index+1:][0]
			command_line = command_line[:index]
			# print(command_line, file_name)
			last_out = open(file_name, "w")

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
			echo_PID_to_user(p.pid, original)
			pid_to_process[p.pid] = p
			pid_to_command[p.pid] = original

		elif command == "bg":
			if len(command_line) < 2 or not command_line[1].isdecimal():
				print("Please enter PID of process to background")
				continue
			pid = int(command_line[1])
			if pid not in list(pid_to_process.keys()):
				print("Please enter the PID of an existing process. Find the PIDs by using the \'jobs\' command.")
				continue
			arguments = pid_to_process[pid].args
			arguments.append('&')
			pid_to_process[pid].send_signal(signal.SIGCONT)
			p = sbp.Popen(arguments[:])
			echo_PID_to_user(p.pid, original)
			pid_to_process[p.pid] = p
			pid_to_command[p.pid] = original
		elif command == "--help":
			print("\nIn built: \nexit --> end shell process\npwd --> print working directory\ncd"+ 
				"--> change directory\njobs --> print current processes with PIDs\nfg --> foreground a task by" + 
				"passing in a PID\nbg --> background a task by passing in a PID\n--help --> this screen\n" + 
				"Other methods are handled by the binary functions of this UNIX System.\n")
		else:
			try:
				if subcommands and piping:
					print("here\n")
					pid_list, full_pid, process_list = subcommand_and_pipe(command_line, first_in, last_out)
					pid_to_process[full_pid] = process_list
					pid_to_command[full_pid] = original
					echo_PID_to_user(full_pid, original)
					if not background:
						# print("not background")
						print(process_list[-1].communicate()[0].decode("utf-8"))
				elif piping:
					pid_list, full_pid, process_list = pipe(commands_to_pipe, first_in, last_out)
					pid_to_process[full_pid] = process_list
					pid_to_command[full_pid] = original
					echo_PID_to_user(full_pid, original)
					if not background:
						# print("not background")
						print(process_list[-1].communicate()[0].decode("utf-8"))
						# process_list[-1].stdout.flush()
				elif subcommands:
					pid_list, full_pid, process_list = subcommand_chain(command_line, first_in, last_out)
					pid_to_process[full_pid] = process_list
					pid_to_command[full_pid] = original
					echo_PID_to_user(full_pid, original)
					if not background:
						# print("not background")
						print(process_list[-1].communicate()[0].decod("utf-8"))
						# process_list[-1].stdout.flush()
				else:
					p = sbp.Popen(command_line, stdin=first_in, stdout=last_out, stderr=sbp.STDOUT)
					pid_to_process[p.pid] = p
					pid_to_command[p.pid] = original
					echo_PID_to_user(p.pid, original)
					# processes[p.pid] = [p, original]
					if not background:
						p.communicate()
			except PermissionError:
				print("Permission Error: not a binary command or builtin or one you do not have acces to. Run --help for more info")
				continue
loop()