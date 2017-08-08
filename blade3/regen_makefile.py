#!/usr/bin/python

# -*- coding: utf-8 -*-

__author__ = 'liuyong@agora.io(Yong Liu)'

import os, sys, subprocess
from color_print import ColorPrint

# get packages, deps_graph, rule_types
exec file(sys.argv[1]).read()

cmd = ["bash", "./build_tools/blade3/gen_makefile.sh"] + [(os.path.dirname(p)[2:] + "/BUILD") for p in packages]
ret = subprocess.call(" ".join(cmd), shell=True)
sys.exit(ret)
