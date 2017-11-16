import multiprocessing
from PyQt5 import QtCore
from time import sleep


def run_process():
    q = multiprocessing.Queue()
    p = multiprocessing.Process(target=does_something, args=(q,))

    # This still hangs. Maybe use a thread on the UI side of process

    p.start()
    while True:
        r = q.get()
        QtCore.QCoreApplication.processEvents()
        if r is None:
            break
        else:
            print(r)
    # print("stopping")
    # p.join()
    print("Here")


def does_something(q):
    sleep(2)
    q.put("Runnign my process")
    q.put(None)
