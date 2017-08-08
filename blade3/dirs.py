#!/usr/bin/env python

# -*- coding: utf-8 -*-

__author__ = 'liuyong@agora.io(Yong Liu)'

import sys, os

current_file_dir = os.path.dirname(__file__)

build_dir = ".build"
makefile_header = current_file_dir + "/Makefile.header"

settings_list = ["debug",
                 "release",
                 ]
