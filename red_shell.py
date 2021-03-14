import os
import getpass
import sys
import signal
import shlex
import pipes
import logging
import readline
import traceback
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
			print("PID: " + str(pid) + ") " + pid_to_command[pid]+ " Return Code: " 
				+ str(pid_to_process[pid].returncode))
			to_remove.append(pid)

	[pid_to_process.pop(proc) for proc in to_remove]
	[pid_to_command.pop(proc) for proc in to_remove]
	for i in pipe_ids:
		clean_pipe(pid_to_process, pid_to_command, i)

def signal_handler(pid_to_process, sig):
	def _handler(signal, frame):
		print("signal recieved: ", signal)
		print("signal sent: ", sig)
		print(pid_to_process)
		try:
			pid_to_process[list(pid_to_process.keys())[0]].send_signal(sig)
			# os.kill(, sig)
			print("in try, in handler, Return Code: ", pid_to_process[list(pid_to_process.keys())[-1]].returncode)
			traceback.print_stack()
		except KeyError:
			print("K")
			pass
	return _handler

def handler(signal, frame):
	print("signal recieved: ", signal)
	pass

def stp_handler(pid_history, paused_commands, pid_to_process, pid_to_command):
	def _handler(signal, frame):
		print("signal recieved: ", signal)
		# print(pid_to_process)
		try:
			to_remove = pid_history[-1]
		except IndexError:
			raise NoPastCommandsError
		
		if pid_history[-1] not in list(paused_commands.keys()):
			to_remove = pid_history[-1]
			paused_commands[to_remove] = pid_to_process[to_remove]
			pid_to_process.pop(to_remove)
		else:
			raise ForegroundError

		raise SigStopError
	return _handler

def pipe(commands_to_pipe, first_in, last_out, fn):
	first, last = commands_to_pipe[0], commands_to_pipe[-1]
	process = sbp.Popen(first, stdin = first_in, stdout=sbp.PIPE, preexec_fn = fn)
	pid_list = [process.pid]
	process_list = [process]
	out = process.stdout

	for command in commands_to_pipe[1:-1]:
		previous = process

		process = sbp.Popen(command, stdin=out, stdout=sbp.PIPE, preexec_fn = fn)
		out = process.stdout

		previous.stdout.close()

		pid_list.append(process.pid)
		process_list.append(process)
		
	process = sbp.Popen(last, stdin=out, stdout=last_out, preexec_fn = fn)
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

def subcommand_chain(commands, first_in, last_out, fn):
	# print(commands)
	process = sbp.Popen(commands[0], stdin=first_in, stdout=sbp.PIPE, preexec_fn = fn)
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
		process = sbp.Popen(i, stdout=sbp.PIPE, preexec_fn = fn)
		pid_list.append(process.pid)
		process_list.append(process)
		args = process.stdout
		previous.stdout.close()
		# print(args)
	
	last = commands[-1]
	if type(last) is not list:
			last = [last]
	last.extend(args)
	process = sbp.Popen(last, stdout=last_out, preexec_fn = fn)
	pid_list.append(process.pid)
	process_list.append(process)
	# args = process.communicate()[0].decode("utf-8")
	return pid_list, tuple(pid_list), process_list

def subcommand_and_pipe(commands, first_in, last_out, fn):
	pid_list = []
	process_list = []
	first, last = commands[0], commands[-1]
	# print(commands) 
	# print(commands[1:-1])
	if any(["$" in i for i in first]):
		to_run = parse_subcommands(first)
		print(to_run)
		temp_pid_list, temp_full_pid, temp_process_list = subcommand_chain(to_run, first_in, sbp.PIPE, fn)
		pid_list.extend(temp_pid_list)
		process_list.extend(temp_process_list)
		process = process_list[-1]
	else:
		process = sbp.Popen(first, stdin = first_in, stdout=sbp.PIPE, preexec_fn = fn)
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
			temp_pid_list, temp_full_pid, temp_process_list = subcommand_chain(to_run, out, sbp.PIPE, fn)
			pid_list.extend(temp_pid_list)
			process_list.extend(temp_process_list)
			process = process_list[-1]
		else:
			process = sbp.Popen(proc, stdin=out, stdout=sbp.PIPE, preexec_fn = fn)
			pid_list.append(process.pid)
			process_list.append(process)

		out = process.stdout
		previous.stdout.close()
		# print(out.read())

	if any(["$" in i for i in last]):
		to_run = parse_subcommands(last)
		print(to_run)
		temp_pid_list, temp_full_pid, temp_process_list = subcommand_chain(to_run, out, last_out, fn)
		pid_list.extend(temp_pid_list)
		process_list.extend(temp_process_list)
		process = process_list[-1]
	else:
		process = sbp.Popen(last, stdin = out, stdout=last_out, preexec_fn = fn)
		pid_list.append(process.pid)
		process_list.append(process)

	return pid_list, tuple(pid_list), process_list

def echo_PID_to_user(pid, original):
	print("PID: " + str(pid) + ") " + original)

class SigStopError(Exception):
	pass

class ForegroundError(Exception):
	pass

class NoPastCommandsError(Exception):
	pass

def loop():
	cwd = os.getcwd()
	# past_commands = set()
	pid_to_process= {}
	pid_to_command = {}
	paused_commands = {}
	pid_history = []
	# process_order = set()
	# foreground = -1
	def background_signal_handler():
		signal.signal(signal.SIGINT, signal.SIG_IGN)
		signal.signal(signal.SIGTSTP, signal.SIG_IGN)
	# def foreground_signal_handler():
	# 	signal.signal(signal.SIGTSTP, signal.SIGTSTP)
	# signal.signal(signal.SIGTSTP, )
	signal.signal(signal.SIGINT, handler)
	signal.signal(signal.SIGTSTP, stp_handler(pid_history, paused_commands, pid_to_process, pid_to_command))

	# signal.signal(signal.SIGTSTP, signal_handler(pid_to_process, signal.SIGSTOP))
	# signal.signal(signal.SIGINT, c_handler(pid_to_process, signal.SIGINT))
	# signal.signal(signal.SIGTSTP, handler)
	# signal.signal(signal.SIGINT, signal.SIG_IGN)
	# signal.signal(signal.SIGPIPE, signal.SIG_DFL)
	while True:
		try:
			clean_processes(pid_to_process, pid_to_command)
			# creation_flags = 0
			# print(paused_commands, pid_to_process)
			pre_fn = None
			# foreground = -1
			# print(pid_to_process)
			# try:
			piping, subcommands = False, False
			in_redirect, out_redirect, first_in, last_out = None, None, None, None
			command_line, background, original = get_input()
			if background:
				# pre_fn = background_signal_handler
				pre_fn = lambda: signal.pthread_sigmask(signal.SIG_BLOCK, (signal.SIGINT, signal.SIGTSTP))
				# pass
			# commands_to_run = command_line[:]
			# print("Initial parse: " + str(command_line))
			# print("foreground PID: ", foreground)
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
				readline.write_history_file(history_file)
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
					print("Paused Processess:")
					for pid in paused_commands:
						print("PID: " + str(pid) + ") " + pid_to_command[pid])
					print("\nOngoing Processess: ")
					ongoing = [pid for pid in pid_to_command if pid not in paused_commands]
					if len(ongoing) < 1:
						print("None")
					else:
						for ongoing in pid_to_command:
							# print(proc.args)
							if pid not in paused_commands:
								print("PID: " + str(pid) + ") " + pid_to_command[pid])
					print()
				# if len(paused_commands > 0)
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
				previous = pid_to_command[pid][:-1]
				# pid_to_process[pid].send_signal(signal.SIGSTOP)
				pid_to_process[pid].kill()
				p = sbp.Popen(arguments[:-1])
				echo_PID_to_user(p.pid, previous)
				pid_to_process[p.pid] = p
				pid_to_command[p.pid] = previous
			elif command == "bg":
				if len(command_line) < 2 or not command_line[1].isdecimal():
					print("Please enter PID of process to background")
					continue
				pid = int(command_line[1])
				if pid not in list(pid_to_process.keys()):
					print("Please enter the PID of an existing process. Find the PIDs by using the \'jobs\' command.")
					continue
				arguments = pid_to_process[pid].args
				previous = pid_to_command[pid] + " &"
				arguments.append('&')
				# pid_to_process[pid].send_signal(signal.SIGSTOP)
				pid_to_process[pid].kill()

				pre_fn = lambda: signal.signal(signal.SIGINT, signal.SIG_IGN)
				# pre_fn = lambda: signal.pthread_sigmask(signal.SIG_BLOCK, (signal.SIGINT, signal.SIGTSTP))

				p = sbp.Popen(arguments[:], preexec_fn = pre_fn)
				echo_PID_to_user(p.pid, previous)
				pid_to_process[p.pid] = p
				pid_to_command[p.pid] = previous
			elif command == "--help":
				print("\nIn built: \nexit --> end shell process\npwd --> print working directory\ncd"+ 
					"--> change directory\njobs --> print current processes with PIDs\nfg --> foreground a task by" + 
					"passing in a PID\nbg --> background a task by passing in a PID\n--help --> this screen\n" + 
					"Other methods are handled by the binary functions of this UNIX System.\n")
			else:
				try:
					if subcommands and piping:
						print("here\n")
						pid_list, full_pid, process_list = subcommand_and_pipe(command_line, first_in, last_out, pre_fn)
						pid_to_process[full_pid] = process_list
						pid_to_command[full_pid] = original
						echo_PID_to_user(full_pid, original)
						pid_history.append(full_pid)
						if not background:
							# print("not background")
							foreground_task = [full_pid, process_list]
							print(process_list[-1].communicate()[0].decode("utf-8"))
					elif piping:
						pid_list, full_pid, process_list = pipe(commands_to_pipe, first_in, last_out, pre_fn)
						pid_to_process[full_pid] = process_list
						pid_to_command[full_pid] = original
						echo_PID_to_user(full_pid, original)
						pid_history.append(full_pid)
						if not background:
							# print("not background")
							print(process_list[-1].communicate()[0].decode("utf-8"))
							# foreground_task = None
							# process_list[-1].stdout.flush()
					elif subcommands:
						pid_list, full_pid, process_list = subcommand_chain(command_line, first_in, last_out, pre_fn)
						pid_to_process[full_pid] = process_list
						pid_to_command[full_pid] = original
						echo_PID_to_user(full_pid, original)
						pid_history.append(full_pid)
						if not background:
							# print("not background")
							print(process_list[-1].communicate()[0].decod("utf-8"))
							# foreground_task = None
							# process_list[-1].stdout.flush()
					else:
						p = sbp.Popen(command_line, stdin=first_in, stdout=last_out, stderr=sbp.STDOUT, 
							preexec_fn=pre_fn)
						pid_to_process[p.pid] = p
						pid_to_command[p.pid] = original
						echo_PID_to_user(p.pid, original)
						pid_history.append(p.pid)
						# foreground = p.pid
						# print(foreground)
						# processes[p.pid] = [p, original]
						if not background:
							p.communicate()
							# foreground = -1
				except PermissionError:
					print("Permission Error: not a binary command or builtin or one you do not have acces to." + 
						" Run --help for more info")
					continue
				# signal.signal(signal.SIGTSTP, signal_handler(foreground, pid_to_process, signal.SIGSTOP))
		except SigStopError:
			continue
		except ForegroundError:
			print("Currently at the foreground, no process to pause.")
			continue
		except NoPastCommandsError:
			print("No past commands yet.")
			continue

# NOTE: this code for history completion was taken completely from: https://pymotw.com/2/readline/ 
# All credit to them, I just maniupulated which lines were called where to suit this program

LOG_FILENAME = 'debug.txt'
logging.basicConfig(filename=LOG_FILENAME, level=logging.DEBUG)
history_file = 'history.txt'

def get_history_items():
	return [readline.get_history_item(i) for i in xrange(1, readline.get_current_history_length() + 1)]

class HistoryCompleter(object):
	def __init__(self):
		self.matches = []
		return

	def complete(self, text, state):
		response = None
		if state == 0:
			history_values = get_history_items()
			logging.debug('history: %s', history_values)
			if text:
				self.matches = sorted(h 
				for h in history_values 
				if h and h.startswith(text))
		else:
			self.matches = []
		logging.debug('matches: %s', self.matches)
		try:
			response = self.matches[state]
		except IndexError:
			response = None
		logging.debug('complete(%s, %s) => %s', 
				repr(text), state, repr(response))
		return response

if os.path.exists(history_file):
	readline.read_history_file(history_file)

readline.set_completer(HistoryCompleter().complete)

# Use the tab key for completion
readline.parse_and_bind('tab: complete')

loop()