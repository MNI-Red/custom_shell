import os
import getpass
import sys
import shlex

# print(getpass.getuser())



def loop():
	cwd = os.getcwd()
	while True:
		command_line = shlex.split(input(str(getpass.getuser()) + " " + str(os.getcwd()) + " > "))
		print(command_line)
		command = command_line[0]
		if command == "ex":
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
		else:
			for root, dirs, files in os.walk(cwd):
				for file in files:
					print(file)
loop()