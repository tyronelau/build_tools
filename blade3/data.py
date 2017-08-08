#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'liuyong@agora.io(Yong Liu)'

import package
import rule
import cc
import sys
from dirs import settings_list

"""
It defines genrule build rule
"""

class CCData(cc.CCLibrary):
  """
    cc_data(name = "",
            srcs = [""]
	   )
  """
  buildName = "cc_data"

  def __init__(self, **kwargs):
    cc.CCLibrary.__init__(self, **kwargs)
    self.is_library = 0 
    self.is_data = 1 

  def exportLibPathList(self, settings_name):
    return []

  def exportLibDirList(self, settings_name):
    return []

  def exportLibNameList(self):
    return []

  def dump(self):
    print "\tdata: ", self.ruleName
    for f in self.srcsList:
      print "\t\tfile: ", f

  def emitMake(self, f):
    ## generate empty dependency rule.
    settings = list(settings_list)
    settings.append("struct_check_dbg")
    settings.append("struct_check_opt")
    for setting in settings:
      print >>f, "%s: \n\n" %(self.makeTargetName(setting))

