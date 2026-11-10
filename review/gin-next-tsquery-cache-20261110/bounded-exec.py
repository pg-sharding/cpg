#!/usr/bin/env python3
"""Linux replay wrapper; 3GB address-space cap and nice 10, then exec the command."""
import argparse
import os
import resource
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('command',nargs=argparse.REMAINDER)
a=p.parse_args();assert a.command
resource.setrlimit(resource.RLIMIT_AS,(3000000000,3000000000))
current=os.getpriority(os.PRIO_PROCESS,0)
if current<10:os.nice(10-current)
assert os.getpriority(os.PRIO_PROCESS,0)==10
os.execvp(a.command[0],a.command)
