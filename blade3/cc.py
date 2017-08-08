#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'liuyong@agora.io(Yong Liu)'

import subprocess
import sys
import os

import package
import rule
import glob
from dirs import build_dir
from dirs import settings_list

"""
It deals with cc_library, cc_binary, cc_lib, cc_test
"""

emitted_target_names = set()
emitted_pub_packages = set()

def simplifyDepList(dep_list):
  """去除 DepList 中的重复项.
     由于 gnu linker 要求只能前面的项依赖后面的项
     因此对于重复项，需要去除排在前面的，保留排在最后的
  """
  cp = list(dep_list)
  cp.reverse()
  r = set()
  res = []
  for a in cp:
    if a not in r: res.append(a)
    r.add(a)
  res.reverse()
  return res

class CCLibrary(rule.Rule):
  """
   create a cpp library with libname.a
   cc_library(name = "",
              srcs = ["", ""],
              deps = ["", ""],
              cppflags = ["", ""],
              cflags = ["", ""],
              cxxflags = ["", ""],
              exclude = ["", ""],
             )
  """
  buildName = "cc_library"

  def __init__(self, **kwargs):
    if "name" not in kwargs:
      print >> sys.stderr, "Must have a 'name' argument, see %s/BUILD " \
          "for details" % package.currentPackage.packageName
      sys.exit(-1)

    if "srcs" not in kwargs:
      print >> sys.stderr, "Must have a 'srcs' argument for //%s/BUILD:%s" \
          %(package.currentPackage.packageName, kwargs["name"])
      sys.exit(-1)

    rule.Rule.__init__(self, kwargs["name"], package.currentPackage)

    self.srcsList = kwargs["srcs"]
    self.checkArguments("srcs", self.srcsList)
    self.srcsList = self.expandFileList(self.srcsList, False)
    if "deps" in kwargs:
      self.depsList = kwargs["deps"]
    else:
      self.depsList = []
    self.depRulesList = []
    self.package.addRule(self)
    self.checkArguments("deps", self.depsList)

    self.exclude_list = []
    if "excludes" in kwargs:
      self.exclude_list = kwargs["excludes"]
    # filter srcs by excludes
    self.checkArguments("excludes", self.exclude_list)
    self.exclude_list = self.expandFileList(self.exclude_list, True)
    self.srcsList = self.filterSrc()
    self.checkBaseName(self.srcsList)

    if "cppflags" in kwargs:
      self.cppflags = kwargs["cppflags"]
    else:
      self.cppflags = []
    self.checkArguments("cppflags", self.cppflags)

    if "cflags" in kwargs:
      self.cflags = kwargs["cflags"]
    else:
      self.cflags = []
    self.checkArguments("cflags", self.cflags)

    if "cxxflags" in kwargs:
      self.cxxflags = kwargs["cxxflags"]
    else:
      self.cxxflags = []

    git = subprocess.Popen(["git", "describe", "--tags", "--always"],
                           cwd="media_server_balancer", stdout=subprocess.PIPE)

    version = git.stdout.read().strip()

    self.cxxflags.append('-DGIT_DESC=\\\"%s\\"' %version)

    self.checkArguments("cxxflags", self.cxxflags)

    # TODO(liuyong): 这个检查没有生效, 因为 self.buildName 的值不对
    if self.buildName == "library" and "ldflags" in kwargs:
      print >>sys.stderr, "can't set ldflags for a library, ldflags can only be " \
          "used while a binary target is declared"

      print >>sys.stderr, "For error details, please check //%s/BUILD:%s" \
          %(self.package.packageName, self.ruleName)
      sys.exit(-1)

    if "src" in kwargs:
      print "did you mean 'srcs' instead of 'src'? in //%s/BUILD:%s" \
          % (self.package.packageName, self.ruleName)
      sys.exit(-1)

    self.is_library = 1

    self.compile_flags = ""
    for flag in self.cflags + self.cxxflags:
      self.compile_flags += "%s " % flag

  def checkBaseName(self, src_list):
    c_or_cc = {}
    for f in src_list:
      # 检查没有同名的 .cc 或 .c
      base_name, ext = os.path.splitext(f)
      if ext != ".cpp" and ext != ".c": continue
      if base_name in c_or_cc:
        print
        print "ERROR: '//%s/BUILD:%s' has conflict source filenames:\n%s\n%s" \
            %(self.package.packageName, self.ruleName, c_or_cc[base_name], f)
        sys.exit(-1)
      c_or_cc[base_name] = f

  def checkSrcs(self):
    # 该函数不能在 __init__ 中调用, 需要初始化完成后才行
    for f in self.srcsList:
      if f.startswith("/") or f.find("..") != -1:
        print "Source file '%s' of '//%s/BUILD:%s' must be under package's directory" \
            % (f, self.package.packageName, self.ruleName)
        sys.exit(-1)

      if self.is_proto:
        if not f.endswith(".proto"):
          print "Source file '%s' of '//%s/BUILD:%s' must be .proto" \
              % (f, self.package.packageName, self.ruleName)
          sys.exit(-1)
        else:
          continue

      if self.is_shell_script or self.is_script_test:
        if not f.endswith(".sh"):
          print "Source file '%s' of '//%s/BUILD:%s' must be .sh" \
              % (f, self.package.packageName, self.ruleName)
          sys.exit(-1)
        else:
          continue

      if self.is_data: continue

      if self.is_binary or self.is_unittest or self.is_library \
         or self.is_pyext or self.is_mpi or self.is_jni_used:
        if not f.endswith(".cc") and not f.endswith(".c") and not f.endswith(".cpp"):
          print "Source file '%s' of '//%s/BUILD:%s' must be .c or .cc" \
              % (f, self.package.packageName, self.ruleName)
          sys.exit(-1)

  def expandFileList(self, file_list, allow_not_found):
    res = []
    for f in file_list:
      fullPath = os.path.join(self.package.packageName, f)
      matched = glob.glob(fullPath)
      if not allow_not_found and len(matched) == 0:
        print "Source file '%s' of '//%s/BUILD:%s' doesn't exists" \
            %(f, self.package.packageName, self.ruleName)
        sys.exit(-1)

      res += [os.path.relpath(a, self.package.packageName) for a \
              in matched]
    return res

  def checkArguments(self, name, value):
    res = True
    if type(value) != type([]):
      res = False
    if res:
      for a in value:
        if type(a) != type(""):
          res = False
    if not res:
      print "The parameter '%s' of //%s/BUILD:%s must be a list of strings" \
          % (name, self.package.packageName, self.ruleName)
      sys.exit(-1)

  def filterSrc(self):
    res = []
    for src in self.srcsList:
       if src in self.exclude_list:
          continue
       res.append(src)
    return res

  def dump(self):
    print "\tlibrary: ", self.ruleName
    for src in self.srcsList:
      print "\t\tsource: ", src
    for rule in self.depRulesList:
      print "\t\tdeps on: //%s/BUILD:%s" % (rule.package.packageName, rule.ruleName)

  def libraryName(self):
     # like libbase.a
     return "lib%s.a" % self.ruleName.lower()

  def targetRootDir(self, settings_name):
    return os.path.join(build_dir, settings_name, "targets")

  def targetDir(self, settings_name):
    return os.path.join(self.targetRootDir(settings_name), self.package.packageName)

  def libraryPath(self, settings_name):
    return os.path.join(self.targetDir(settings_name), self.libraryName())

  def makeTargetName(self, settings_name):
    # the make rule target of this build rule
    return self.libraryPath(settings_name)

  def pubTargetRootDir(self, settings_name):
    return os.path.join("pub", settings_name, "targets")

  def pubTargetDir(self, settings_name):
    return os.path.join(self.pubTargetRootDir(settings_name), self.package.packageName)

  def pubLibraryPath(self, settings_name):
    return os.path.join(self.pubTargetDir(settings_name), self.libraryName())

  def pubMakeTargetName(self, settings_name):
    # the make rule target of this build rule
    return self.pubLibraryPath(settings_name)

  def exportLibNameList(self):
    # such as ["base"] for libbase.a
    res = [self.ruleName]
    for dep in self.depRulesList:
      res = res + dep.exportLibNameList()
    return simplifyDepList(res)

  def depPackageNames(self):
    res = set()
    for dep in self.depRulesList:
      res.add(dep.package.packageName)
    return " ".join(res)

  def depPBHeaderPathSet(self):
    res = set()
    for dep in self.depRulesList:
      res = res | dep.depPBHeaderPathSet()
      if dep.is_proto:
        res = res | dep.genHeaderPathSet()
      # if dep.is_proto:
      #   res = res | dep.genHeaderPathSet()
      #   res = res | dep.depPBHeaderPathSet()
      # else:
      #   res = res | dep.depPBHeaderPathSet()
    return res

  def exportLibPathList(self, settings_name):
    # such as ["build/base/libbase.a"] for base rule on package base
    if self.package.isPubOnly:
      res = [self.pubLibraryPath(settings_name)]
    else:
      res = [self.libraryPath(settings_name)]
    for dep in self.depRulesList:
      res = res + dep.exportLibPathList(settings_name)
    return simplifyDepList(res)

  def depLibPathList(self, settings_name):
    # such as ["build/base/libbase.a"] for base rule on package base
    res = []
    for dep in self.depRulesList:
      res = res + dep.exportLibPathList(settings_name)
    return simplifyDepList(res)

  def exportLibDirList(self, settings_name):
    # such as ["build/base"] or ["build/debug"]
    res = [os.path.join(build_dir, settings_name, "targets", self.package.packageName)]
    for dep in self.depRulesList:
      res = res + dep.exportLibDirList(settings_name)
    return simplifyDepList(res)

  def objectRoot(self, settings_name):
    # such as "bulid/base/objs"
    return os.path.join(build_dir, settings_name, "objs")

  def objectDir(self, obj, settings_name):
    # such as "build/base/objs/base"
    # if obj is t1/t.o, return "build/base/objs/base/t1
    dir_name = os.path.dirname(obj)
    if dir_name == "":
      return os.path.join(self.objectRoot(settings_name), self.package.packageName)
    else:
      return os.path.join(self.objectRoot(settings_name), self.package.packageName, dir_name)

  def objectPath(self, fileName, settings_name):
    # such as "build/base/objs/base/t.o"
    return os.path.join(self.objectDir("", settings_name), fileName)

  def objectPathList(self, settings_name):
    # such as ["build/base/objs/base/t.o", "build/base/objs/base/s.o"]
    pathList = ""
    for src in self.srcsList:
      obj = os.path.splitext(src)[0] + ".o"
      pathList = "%s %s" % (pathList, self.objectPath(obj, settings_name))
    return pathList

  def srcPath(self, fileName):
    # such as "base/t.cc"
    return os.path.join(self.package.packageName, fileName)

  def compileTool(self, fileName, settings_name):
    res = ""
    cc_or_cxx = "CC" if fileName.endswith(".c") else "CXX"
    res = "${%s_%s} ${%s_CPPFLAGS} ${%s_%sFLAGS}" \
        % (settings_name.upper(), cc_or_cxx, settings_name.upper(), settings_name.upper(),
           "CXX" if cc_or_cxx == "CXX" else "C")

    if len(self.cppflags) > 0:
      res = res + " %s" % " ".join(sorted(set(self.cppflags)))

    if cc_or_cxx == "CC" and len(self.cflags) > 0:
      res = res + " %s" % " ".join(sorted(set(self.cflags)))

    if cc_or_cxx == "CXX" and len(self.cxxflags) > 0:
      res = res + " %s" % " ".join(sorted(set(self.cxxflags)))

    # res += " ${WARN_AS_ERROR}"
    return res

  def protoTarget(self):
    res = ""
    for dep in self.depRulesList:
      if dep.is_proto == 1:
        res += "%s " % dep.makeProtoTarget()
    return res

  def emitSrcMake(self, f):
    for src in self.srcsList:
      for settings_name in settings_list:
        obj = os.path.splitext(src)[0] + ".o"
        depfile = os.path.splitext(src)[0] + ".d"
        obj_dir = os.path.dirname(self.objectPath(obj, settings_name))
        print >>f, "%s: %s %s" % (self.objectPath(obj, settings_name), self.protoTarget(), self.srcPath(src))
        print >>f, '\t@${PRINT} "_____compile %s %s"' % (settings_name, self.srcPath(src))
        print >>f, "\tif [ ! -x %s ]; then mkdir -p %s; fi" % (obj_dir, obj_dir)
        print >>f, "\t%s -o %s -c %s" % (self.compileTool(src, settings_name),
                                         self.objectPath(obj, settings_name),
                                         self.srcPath(src))
        print >>f, "\n"
        print >>f, "-include %s" % self.objectPath(depfile, settings_name)
        print >>f, "\n"

  def staticCheckTarget(self):
    return build_dir + "/static_check/" + self.package.packageName + "/BUILD/" + self.ruleName

  def emitStaticCheck(self, f):
    if self.is_proto: return
    if self.is_data: return

    all_static_check_result = []
    static_check_root_dir = build_dir + "/static_check"
    for src in self.srcsList:
      # for static check
      check_result_file = static_check_root_dir + "/" + self.srcPath(src)
      static_check_dir = os.path.dirname(check_result_file)
      obj = os.path.splitext(src)[0] + ".o"
      print >>f, "%s: %s" % (check_result_file, self.objectPath(obj, settings_list[0]))
      print >>f, '\t@${PRINT} "_____static_check %s"' % self.srcPath(src)
      print >>f, "\tif [ ! -x %s ]; then mkdir -p %s; fi" % (static_check_dir, static_check_dir)
      print >>f, "\t${STATIC_CHECKER} %s" % (self.srcPath(src))
      print >>f, "\t@touch %s" % check_result_file
      print >>f, "\n"
      all_static_check_result.append(check_result_file)

    # all static checking
    check_result_file = self.staticCheckTarget()
    static_check_dir = os.path.dirname(check_result_file)
    print >>f, "%s: %s" % (check_result_file, " ".join(all_static_check_result))
    print >>f, "\t@if [ ! -x %s ]; then mkdir -p %s; fi" % (static_check_dir, static_check_dir)
    print >>f, "\t@touch %s" % check_result_file
    print >>f, "\n"

  def emitSelfMake(self, f):
    self.emitSrcMake(f)

    for settings_name in settings_list:
      print >>f, "%s: %s %s %s" % (self.makeTargetName(settings_name),
                                self.depPackageNames(),
                                " ".join(self.depPBHeaderPathSet()),
                                self.objectPathList(settings_name))
      print >>f, '\t@${PRINT} "_____link [%s]"' % self.makeTargetName(settings_name)
      print >>f, "\tif [ ! -x %s ]; then mkdir -p %s; fi" \
          % (self.targetDir(settings_name), self.targetDir(settings_name))
      print >>f, "\t${AR} %s %s" % (self.makeTargetName(settings_name), self.objectPathList(settings_name))
      print >>f, "\n"

  def getDepLayoutFiles(self, setting):
    targets = []
    for dep in self.depRulesList:
      targets.append(dep.makeTargetName(setting) + ".merge")
    return " ".join(targets)

  def emitPubMake(self, f):
    packageDir = self.package.packageName
    if self.package.packageName not in emitted_pub_packages:
      emitted_pub_packages.add(self.package.packageName)
      pubDir = "pub/src/" + packageDir
      parentDir = os.path.abspath(os.path.dirname(packageDir))
      print >>f, "%s: %s" % (packageDir, pubDir)
      print >>f, '\t@${PRINT} "_____symbolic link [%s]"' % packageDir
      print >>f, "\tif [ ! -x %s ]; then mkdir -p %s; fi" % (parentDir, parentDir)
      print >>f, "\tln -f -s -t %s %s" % (parentDir, os.path.relpath(pubDir, parentDir))
      print >>f, "\n"

    for settings_name in settings_list:
      print >>f, "%s: %s %s" % (self.makeTargetName(settings_name), packageDir,
                                self.pubMakeTargetName(settings_name))
      print >>f, '\t@${PRINT} "_____symbolic link [%s]"' % self.makeTargetName(settings_name)
      print >>f, "\tif [ ! -x %s ]; then mkdir -p %s; fi" % (self.targetDir(settings_name),
                                                             self.targetDir(settings_name))
      print >>f, "\tln -f -s -t %s %s" % (self.targetDir(settings_name),
                                          os.path.relpath(self.pubMakeTargetName(settings_name),
                                                          self.targetDir(settings_name)))
      print >>f, "\n"

  def emitDependencies(self, f):
    for dep in self.depRulesList:
      dep.emitDependencies(f)

  def emitMake(self, f):
    self.checkSrcs()

    tn = self.makeTargetName(settings_list[0])
    if tn in emitted_target_names:
      return
    emitted_target_names.add(tn)

    if self.package.isPubOnly:
      self.emitPubMake(f)
    else:
      self.emitSelfMake(f)

    for dep in self.depRulesList:
      dep.emitMake(f)

    self.emitDependencies(f)

class CCBinary(CCLibrary):
  """
   cc_binary(name = "",
             srcs = ["", ""],
             deps = ["", ""],
             cppflags = ["", ""],
             cflags = ["", ""],
             cxxflags = ["", ""],
             ldflags = ["", ""],
            )
  """
  buildName = "cc_binary"

  def __init__(self, **kwargs):
    CCLibrary.__init__(self, **kwargs)

    if "ldflags" in kwargs:
      self.ldflags = kwargs["ldflags"]

    self.ldflags.append("-g")

    self.is_binary = 1
    self.is_library = 0

  def getLinkerFlags(self):
    res = ""
    for flag in simplifyDepList(self.ldflags):
      res += "%s " % flag
    return res

  def dump(self):
    print "\tbinary: ", self.ruleName
    for src in self.srcsList:
      print "\t\tsource:", src
    for rule in self.depRulesList:
      print "\t\tdeps on: //%s/BUILD:%s" % (rule.package.packageName, rule.ruleName)

  def makeTargetName(self, settings_name):
    # such as "build/base/base_bin"
    return os.path.join(build_dir, settings_name, "targets", self.package.packageName, self.ruleName)

  def exportLibNameList(self):
    res = []
    for dep in self.depRulesList:
      res = res + dep.exportLibNameList()
    return simplifyDepList(res)

  def exportLibPathList(self, settings_name):
    res = []
    for dep in self.depRulesList:
      res = res + dep.exportLibPathList(settings_name)
    return simplifyDepList(res)

  def exportLibDirList(self, settings_name):
    res = []
    for dep in self.depRulesList:
      res = res + dep.exportLibDirList(settings_name)
    return simplifyDepList(res)

  def emitSrcMake(self, f):
    CCLibrary.emitSrcMake(self, f)

    ## an ugly work-around for layout checking..
    # src = ".build/meta_cc/%s/%s.cc" % (self.package.packageName, self.ruleName)

    # for settings_name in settings_list:
    #   obj = ".build/%s/meta_objs/%s/%s.o" % (settings_name, self.package.packageName, self.ruleName)
    #   dep_file = ".build/%s/meta_objs/%s/%s.d" % (settings_name, self.package.packageName, self.ruleName)
    #   obj_dir = os.path.dirname(obj)
    #   print >>f, "%s: %s" % (obj, src)
    #   print >>f, '\t@${PRINT} "_____compile %s %s"' % (settings_name, src)
    #   print >>f, "\tif [ ! -x %s ]; then mkdir -p %s; fi" % (obj_dir, obj_dir)
    #   print >>f, "\t%s -o %s -c %s" % (self.compileTool(src, settings_name), obj, src)
    #   print >>f, "\n"
    #   print >>f, "-include %s" % dep_file
    #   print >>f, "\n"

  def emitMake(self, f):
    tn = self.makeTargetName(settings_list[0])
    if tn in emitted_target_names:
      return
    emitted_target_names.add(tn)

    self.emitSrcMake(f)

    for settings_name in settings_list:
      # meta_obj = ".build/%s/meta_objs/%s/%s.o" % (settings_name, self.package.packageName, self.ruleName)
      print >>f, "%s: %s %s %s %s" % (self.makeTargetName(settings_name),
                                         self.depPackageNames(),
                                         " ".join(self.depPBHeaderPathSet()),
                                         self.objectPathList(settings_name),
                                         " ".join(self.exportLibPathList(settings_name)))
      print >>f, '\t@${PRINT} "_____link [%s]"' % self.makeTargetName(settings_name)
      print >>f, "\tif [ ! -x %s ]; then mkdir -p %s; fi" \
          % (self.targetDir(settings_name), self.targetDir(settings_name))
      print >>f, "\t${%s_CXX} %s %s %s ${%s_LDFLAGS} %s %s -o %s" \
          % (settings_name.upper(), self.objectPathList(settings_name),
             " ".join(self.exportLibPathList(settings_name)),
             self.getLinkerFlags(), settings_name.upper(),
             "", "", self.makeTargetName(settings_name))
      print >>f, "\n"

    for dep in self.depRulesList:
      dep.emitMake(f)

    self.emitDependencies(f)

class CCJNILibrary(CCLibrary):
  """
   cc_jni_library(name = "",
                  srcs = ["", ""],
            )
  """
  buildName = "cc_jni_library"

  def __init__(self, **kwargs):
    CCLibrary.__init__(self, **kwargs)
    self.is_jni_used = 1

  def dump(self):
    print "\tjni_library: ", self.ruleName
    for src in self.srcsList:
      print "\t\tsource: ", src
    for rule in self.depRulesList:
      print "\t\tdeps on: //%s/BUILD:%s" % (rule.package.packageName, rule.ruleName)


class CCMPILibrary(CCLibrary):
  """
   cc_mpi_library(name = "",
                  srcs = ["", ""],
            )
  """
  buildName = "cc_mpi_library"

  def __init__(self, **kwargs):
    CCLibrary.__init__(self, **kwargs)
    self.is_mpi = 1

  def dump(self):
    print "\tmpi_library: ", self.ruleName
    for src in self.srcsList:
      print "\t\tsource: ", src
    for rule in self.depRulesList:
      print "\t\tdeps on: //%s/BUILD:%s" % (rule.package.packageName, rule.ruleName)

class CCMPIBinary(CCBinary):
  '''
   cc_mpi_binary(name = "",
                 srcs = ["", ""],
                 deps = ["", ""],
                )
  '''
  buildName = "cc_mpi_binary"

  def __init__(self, **kwargs):
    CCBinary.__init__(self, **kwargs)
    self.is_mpi = 1

  def dump(self):
    print "\tmpi_binary: ", self.ruleName
    for src in self.srcsList:
      print "\t\tsource:", src
    for rule in self.depRulesList:
      print "\t\tdeps on: //%s/BUILD:%s" % (rule.package.packageName, rule.ruleName)


class CCTest(CCBinary):
  '''
   cc_test(name = "",
           srcs = ["", ""],
           deps = ["", ""],
          )
  '''
  buildName = "cc_test"

  def __init__(self, **kwargs):
    CCBinary.__init__(self, **kwargs)
    self.is_unittest = 1
    for flags in self.ldflags:
      if flags == "-lgtest":
        return

    self.ldflags.append("-lgtest")

  def dump(self):
    print "\ttest: ", self.ruleName
    for src in self.srcsList:
      print "\t\tsource: ", src
    for rule in self.depRulesList:
      print "\t\tdeps on: //%s/BUILD:%s" % (rule.package.packageName, rule.ruleName)


class CCPyExt(CCLibrary):
  """
   cc_pyext(name = "",
             srcs = ["", ""],
             deps = ["", ""],
             cppflags = ["", ""],
             cflags = ["", ""],
             cxxflags = ["", ""],
             ldflags = ["", ""],
            )
  """
  buildName = "cc_pyext"

  def __init__(self, **kwargs):
    CCLibrary.__init__(self, **kwargs)
    self.is_library = 0
    self.is_pyext = 1

    self.ldflags = []
    if "ldflags" in kwargs:
      self.ldflags = kwargs["ldflags"]

    self.is_library = 0
    self.is_pyext = 1

  def getLinkerFlags(self):
    res = ""
    for flag in simplifyDepList(self.ldflags):
      res += "%s " % flag
    return res


  def dump(self):
    print "\tpyext: ", self.ruleName
    for src in self.srcsList:
      print "\t\tsource:", src
    for rule in self.depRulesList:
      print "\t\tdeps on: //%s/BUILD:%s" % (rule.package.packageName, rule.ruleName)

  def makeTargetName(self, settings_name):
    # such as "build/base/base_bin"
    return os.path.join(build_dir, settings_name, "targets", self.package.packageName, self.ruleName + ".so")

  def exportLibNameList(self):
    res = []
    for dep in self.depRulesList:
      res = res + dep.exportLibNameList()
    return simplifyDepList(res)

  def exportLibPathList(self, settings_name):
    res = []
    for dep in self.depRulesList:
      res = res + dep.exportLibPathList(settings_name)
    return simplifyDepList(res)

  def exportLibDirList(self, settings_name):
    res = []
    for dep in self.depRulesList:
      res = res + dep.exportLibDirList(settings_name)
    return simplifyDepList(res)

  def emitSrcMake(self, f):
    CCLibrary.emitSrcMake(self, f)

    ## an ugly work-around for layout checking..
    src = ".build/meta_cc/%s/%s.cc" % (self.package.packageName, self.ruleName)

    for settings_name in settings_list:
      obj = ".build/%s/meta_objs/%s/%s.o" % (settings_name, self.package.packageName, self.ruleName)
      dep_file = ".build/%s/meta_objs/%s/%s.d" % (settings_name, self.package.packageName, self.ruleName)
      obj_dir = os.path.dirname(obj)
      print >>f, "%s: %s" % (obj, src)
      print >>f, '\t@${PRINT} "_____compile %s %s"' % (settings_name, src)
      print >>f, "\tif [ ! -x %s ]; then mkdir -p %s; fi" % (obj_dir, obj_dir)
      print >>f, "\t%s -o %s -c %s" % (self.compileTool(src, settings_name), obj, src)
      print >>f, "\n"
      print >>f, "-include %s" % dep_file
      print >>f, "\n"

  def emitMake(self, f):
    tn = self.makeTargetName(settings_list[0])
    if tn in emitted_target_names:
      return
    emitted_target_names.add(tn)

    self.emitSrcMake(f)

    # for settings_name in settings_list:
    #   meta_obj = ".build/%s/meta_objs/%s/%s.o" % (settings_name, self.package.packageName, self.ruleName)
    #   print >>f, "%s: %s %s %s %s %s" % (self.makeTargetName(settings_name),
    #                                   self.depPackageNames(),
    #                                   " ".join(self.depPBHeaderPathSet()),
    #                                   self.objectPathList(settings_name),
    #                                   meta_obj,
    #                                   " ".join(self.exportLibPathList(settings_name)))
    #   print >>f, '\t@${PRINT} "_____link [%s]"' % self.makeTargetName(settings_name)
    #   print >>f, "\tif [ ! -x %s ]; then mkdir -p %s; fi" \
    #       % (self.targetDir(settings_name), self.targetDir(settings_name))
    #   print >>f, "\t${%s_CXX} %s %s %s %s ${%s_LDFLAGS} -shared -o %s" \
    #       % (settings_name.upper(), self.objectPathList(settings_name),
    #          " ".join(self.exportLibPathList(settings_name)),
    #          self.getLinkerFlags(), meta_obj, settings_name.upper(),
    #          self.makeTargetName(settings_name))
    #  print >>f, "\n"

    ## merge the cpps' layouts to the binary layout file
    ## and then check the coherences among the libraries.
    # for setting in ["struct_check_dbg", "struct_check_opt"]:
    #   base_name = self.makeTargetName(setting)
    #   print >>f, "%s: %s %s %s %s" % (base_name,
    #                                      self.depPackageNames(),
    #                                      " ".join(self.depPBHeaderPathSet()),
    #                                      self.objectPathList(setting),
    #                                      " ".join(self.exportLibPathList(setting)))
    #   print >>f, '\t@${PRINT} "_____merging the layouts [%s]"' %(base_name)
    #   print >>f, "\tif [ ! -x %s ]; then mkdir -p %s; fi" \
    #       % (self.targetDir(setting), self.targetDir(setting))
    #   fmt_str = "\t@if echo ${STRUCT_CHECK_TOOL} --out_file %s --dot_file %s %s;" + \
    #       " ${STRUCT_CHECK_TOOL} --out_file %s --dot_file %s %s; " + \
    #     "then echo \"layout checking succeeded\"; else dot -Tpng -o %s %s;" + \
    #     "echo \"layout check Failed, please see the dependant graph \033[31m%s\033[m of classes " + \
    #     "required to be updated\"; exit -1; fi\n"

    #   print >>f, fmt_str %(
    #       base_name,
    #       base_name + ".dot",
    #       self.objectPathList(setting),
    #       base_name,
    #       base_name + ".dot",
    #       self.objectPathList(setting),
    #       base_name + ".png",
    #       base_name + ".dot",
    #       base_name + ".png")

    for dep in self.depRulesList:
      dep.emitMake(f)

    self.emitDependencies(f)

