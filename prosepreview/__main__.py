#!/usr/python/python3.11

import prosepreview.cmd
import sys

parser = prosepreview.cmd.Root()
parser(sys.argv[1:])
