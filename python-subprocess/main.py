from subprocess import Popen, PIPE
p = Popen(['cat', 'main.py'], stdout=PIPE)
print(p.stdout.read().decode('utf8'))
