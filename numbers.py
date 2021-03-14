import time
import sys

f = open("out.txt", "a")
for i in range(100000000000):
	f.write(str(i)+"\n")
	f.flush()
	print(i)
	time.sleep(5)