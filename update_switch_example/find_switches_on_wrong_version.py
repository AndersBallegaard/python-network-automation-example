#!/usr/bin/python3
from getpass import getpass
from threading import Thread
import pusher

username = None
password = None
switches = []


def worker():
    global switches

    while len(switches) > 0:
        try:
            switch = switches.pop(0)
            switch.createSSHConnection(username, password)
            switch.gatherFacts()

            if "WS-C2960C-12" in switch.platform:
                if "SE10a" not in switch.software_version:
                    print(switch.hostname)
        except:
            pass


if __name__ == "__main__":
    username = input("Username: ")
    password = getpass()
    switches = pusher.getDevices(username, password)

    tl = []

    for _ in range(0, 15):
        t = Thread(target=worker)
        t.start()
        tl.append(t)

    for t in tl:
        t.join()
