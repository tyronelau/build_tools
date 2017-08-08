#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'liuyong@agora.io(Yong Liu)'


import package
import rule
import cc
import sys

class ShellScript(cc.CCLibrary):
  """
    shell_script(name = "",
                 srcs = [""]
    )
  """
  buildName = "shell_script"

  def __init__(self, **kwargs):
    cc.CCLibrary.__init__(self, **kwargs)
    self.is_library = 0 
    self.is_shell_script = 1 

  def exportLibPathList(self, settings_name):
    return []

  def exportLibDirList(self, settings_name):
    return []

  def exportLibNameList(self):
    return []

  def dump(self):
    print "\tshell_script: ", self.ruleName
    for f in self.srcsList:
      print "\t\tfile: ", f

  def emitMake(self, f):
    pass

# shell script test case
# 脚本编写的测试文件，只有在所有版本的二进制 (dbg/opt/diag_dbg/diag_opt) 编译成功后，才会运行
class SSTest(cc.CCLibrary):
  """
    ss_test(name = "",
            srcs = [""]
           )
  """
  buildName = "ss_test"

  def __init__(self, **kwargs):
    cc.CCLibrary.__init__(self, **kwargs)
    self.is_library = 0 
    self.is_shell_script = 1 
    self.is_script_test = 1 

    for src in self.srcList:
      if not src.endswith("_test.sh"):
        print >> sys.stderr, "file name of shell script test must ended with '_test.sh': %s" % src
        sys.exit(-1)

  def exportLibPathList(self, settings_name):
    return []

  def exportLibDirList(self, settings_name):
    return []

  def exportLibNameList(self):
    return []

  def scriptsPathList(self):
    return [("%s/%s" % (self.package.packageName, filename)) for filename in self.srcsList]

  def dump(self):
    print "\tss_test: ", self.ruleName
    for f in self.srcsList:
      print "\t\tfile: ", f

  def emitMake(self, f):
    pass

