#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'liuyong@agora.io(Yong Liu)'


import package
import rule
import cc
import os, sys
from dirs import build_dir
from dirs import settings_list

"""
It defines genrule build rule
"""
class GenRule(rule.Rule):
  """
    genrule(name = "",
            cmds = [""]
	   )
  """
  buildName = "gen_rule"

  def __init__(self, **kwargs):
    rule.Rule.__init__(self, kwargs["name"], package.currentPackage)
    self.cmdsList = kwargs["cmds"]
    self.srcsList = []
    self.depsList = []
    self.depRulesList = []
    self.package.addRule(self)
    self.emited = False

  def dump(self):
    print "\t", self.ruleName, self.cmdsList

  def emitMake(self, f):
    if self.emited:
      return

    print >>f, "%s.%s : %s/BUILD" % (self.package.packageName, self.ruleName, self.package.packageName)
    for cmd in self.cmdsList:
      print >>f, "\t@%s" % cmd
    print >>f, "\n"

    self.emited = True

class ProtoLibrary(cc.CCLibrary):
  """
    proto_library(name = "",
                  srcs = ["", ""],
	               )
  """
  buildName = "proto_library"

  def __init__(self, **kwargs):
     cc.CCLibrary.__init__(self, **kwargs)
     self.is_proto = 1

  def genSrcPath(self, fileName):
    return "%s/pb/c++/%s.pb.cc" % (build_dir, self.srcPath(fileName)[:-6])

  def genHeaderPath(self, fileName):
    return "%s/pb/c++/%s.pb.h" % (build_dir, self.srcPath(fileName)[:-6])

  def genHeaderPathSet(self):
   result = set()
   for src in self.srcsList:
     result.add(self.genHeaderPath(src))
   return result

  def objectPathList(self, settings_name):
   pathList = ""
   for src in self.srcsList:
     obj = "%s.pb.o" % src[:-6]
     pathList = "%s %s" % (pathList, self.objectPath(obj, settings_name))
   return pathList

  def makeProtoTarget(self):
    res = ""
    for src in self.srcsList:
      res = "%s " % self.genSrcPath(src)
    return res

  def protoPathList(self):
     res = ""
     for src in self.srcsList:
        res += "%s " % self.srcPath(src)
     return res

  def emitSelfMake(self, f):
    for src in self.srcsList:
      print >>f, "%s %s: %s %s" % (self.genSrcPath(src),
                                self.genHeaderPath(src),
                                self.protoTarget(),
                                self.srcPath(src),
                                )
      print >>f, '\t@${PRINT} "_____protoc %s"' % self.srcPath(src)
      print >>f, "\tif [ ! -x %s/pb/c++ ]; then mkdir -p %s/pb/c++; fi" % (build_dir, build_dir)
      print >>f, "\tif [ ! -x %s/pb/py ]; then mkdir -p %s/pb/py; fi" % (build_dir, build_dir)
      print >>f, "\t${PROTOC} --python_out=%s/pb/py --cpp_out=%s/pb/c++ -I./ %s" \
          % (build_dir, build_dir, self.srcPath(src))
      print >>f, "\n"
    
    temp_settings = list(settings_list)
    temp_settings.append("struct_check_dbg")
    temp_settings.append("struct_check_opt")

    for settings_name in temp_settings:
      # Rules to compile cc to o
      for src in self.srcsList:
        obj = "%s.pb.o" % src[:-6]
        depfile = "%s.pb.d" % src[:-6]
        obj_dir = os.path.dirname(self.objectPath(obj, settings_name))
        print >>f, "%s: %s %s %s" % (self.objectPath(obj, settings_name),
                                  self.genSrcPath(src),
                                  " ".join(self.depPBHeaderPathSet()),
                                  " ".join(sorted(set(self.depLibPathList(settings_name))))
                                  )
        print >>f, '\t@${PRINT} "_____compile %s %s"' % (settings_name, self.srcPath(src))
        print >>f, "\tif [ ! -x %s ]; then mkdir -p %s; fi" % (obj_dir, obj_dir)
        print >>f, "\t%s -o %s -c %s" % (self.compileTool(src, settings_name),
                                         self.objectPath(obj, settings_name),
                                         self.genSrcPath(src))
        print >>f, "\n"
        print >>f, "-include %s" % (self.objectPath(depfile, settings_name))
        print >>f, "\n"
    
    for settings_name in settings_list:
      # Linking to lib
      print >>f, "%s: %s" % (self.makeTargetName(settings_name),
                                self.objectPathList(settings_name))
      print >>f, '\t@${PRINT} "_____link [%s]"' % self.makeTargetName(settings_name)
      print >>f, "\tif [ ! -x %s ]; then mkdir -p %s; fi" % (self.targetDir(settings_name),
                                                             self.targetDir(settings_name))
      print >>f, "\t${AR} %s %s" % (self.makeTargetName(settings_name), self.objectPathList(settings_name))
      print >>f, "\n"

    # merge the cpps' layouts to the binary layout file. 
    for setting in ["struct_check_dbg", "struct_check_opt"]:
      base_name = self.makeTargetName(setting)
      print >>f, "%s: %s" % (base_name, self.objectPathList(setting))
      print >>f, '\t@${PRINT} "_____merging the layouts [%s]"' %(base_name)
      print >>f, "\tif [ ! -x %s ]; then mkdir -p %s; fi" \
          % (self.targetDir(setting), self.targetDir(setting))
      fmt_str = "\t@if ${STRUCT_CHECK_TOOL} --out_file %s --dot_file %s %s; " + \
        "then echo \"layout checking succeeded\"; else dot -Tpng -o %s %s;" + \
        "echo \"layout check Failed, please see the dependant graph \033[31m%s\033[m of classes " + \
        "required to be updated\"; exit -1; fi\n"
      print >>f, fmt_str %(
          base_name,
          base_name + ".dot",
          self.objectPathList(setting),
          base_name + ".png",
          base_name + ".dot",
          base_name + ".png")
 
  def emitPubMake(self, f):
    for src in self.srcsList:
      print >>f, "%s %s: %s %s" % (self.genSrcPath(src),
                                self.genHeaderPath(src),
                                self.protoTarget(),
                                self.srcPath(src),
                                )
      print >>f, "\t@${PRINT} _____protoc %s" % self.srcPath(src)
      print >>f, "\tif [ ! -x %s/pb/c++ ]; then mkdir -p %s/pb/c++; fi" % (build_dir, build_dir)
      print >>f, "\tif [ ! -x %s/pb/py ]; then mkdir -p %s/pb/py; fi" % (build_dir, build_dir)
      print >>f, "\t${PROTOC} --python_out=%s/pb/py --cpp_out=%s/pb/c++ -I./ %s" % \
          (build_dir, build_dir, self.srcPath(src))
    print >>f, "\n"

    packageDir = self.package.packageName
    if self.package.packageName not in cc.emitted_pub_packages:
      cc.emitted_pub_packages.add(self.package.packageName)
      pubDir = "pub/src/" + packageDir
      parentDir = os.path.abspath(os.path.dirname(packageDir))
      print >>f, "%s: %s" % (packageDir, pubDir)
      print >>f, '\t@${PRINT} "_____symbolic link [%s]"' % packageDir
      print >>f, "\tif [ ! -x %s ]; then mkdir -p %s; fi" % (parentDir, parentDir)
      print >>f, "\tln -f -s -t %s %s" % (parentDir, os.path.relpath(pubDir, parentDir))
      print >>f, "\n"
    
    temp_settings = list(settings_list)
    temp_settings.append("struct_check_dbg")
    temp_settings.append("struct_check_opt")

    for settings_name in temp_settings:
      print >>f, "%s: %s %s" % (self.makeTargetName(settings_name), packageDir,
                                self.pubMakeTargetName(settings_name))
      print >>f, '\t@${PRINT} "_____symbolic link [%s]"' % self.makeTargetName(settings_name)
      print >>f, "\tif [ ! -x %s ]; then mkdir -p %s; fi" % (self.targetDir(settings_name),
                                                             self.targetDir(settings_name))
      print >>f, "\tln -f -s -t %s %s" % (self.targetDir(settings_name),
                                          os.path.relpath(self.pubMakeTargetName(settings_name),
                                                          self.targetDir(settings_name)))
      print >>f, "\n"
  
class SetPackageAttr:
  """
    set_package_attr()
  """
  buildName = "set_package_attr"

  def __init__(self, **kwargs):
    p = package.currentPackage
    for key in kwargs:
      value = kwargs[key]
      if key != "private":
        print >>sys.stderr, "Unknown argument '%s', in set_package_attr() of //%s/BUILD" % \
            (key, p.packageName);
        sys.exit(-1)
      if value == True:
        p.setPrivate();
      elif value != False:
        print >>sys.stderr, "Invalid value of argument '%s = %s' , in set_package_attr() of //%s/BUILD" % \
            (key, value, p.packageName);
        sys.exit(-1)

