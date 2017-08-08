#!/usr/bin/python

import os, sys

colors = {
  "black": 30,
  "red": 31,
  "green": 32,
  "yellow": 33,
  "blue": 34,
  "magenta": 35,
  "cyan": 36,
  "white": 37,
}
resume = ""
template = "\033[%dm"

def ColorPrint(c, msg):
  if sys.stdout.isatty():
    color = colors[c]
    print "\033[%dm%s\033[m" % (color, msg)
  else:
    print "%s" % msg

if __name__ == "__main__":
  if len(sys.argv) == 1:
    print
    sys.exit(0)
  else:
    ColorPrint(sys.argv[1], " ".join(sys.argv[2:]))
