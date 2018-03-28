import rx
from rx.concurrency import ThreadPoolScheduler
from time import sleep
from random import randint

scheduler = ThreadPoolScheduler(3)

def f(x):
    sleep(0.6)
    print("f>>", x)

def g(x):
    sleep(0.4)
    print("g>>", x)

#u = rx.Observable.interval(100)
def make_u(t):
    i = 0
    while True:
        yield i
        i += 1

u = rx.Observable.interval(100)
v = rx.Observable.range(0, 10).map(lambda i: randint(0,1000))

# u.buffer_with_count(3).subscribe(f)
v.observe_on(scheduler).subscribe(f)
v.observe_on(scheduler).subscribe(g)

input()
