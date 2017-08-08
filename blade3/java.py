#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'liuyong@agora.io(Yong Liu)'


import sys
import os

import package
import rule

"""
java_library: build a .jar from .java
java_binary: make a .jar contains all .jar file, and make a start script
java_lib: rule to export .jar
java_proto: generate .java from .proto
"""

class JavaLibrary(rule.Rule):
  """
    java_library(name = "",
                 srcs = ["",""],
                 deps = ["", ""]
                )
  """
  buildName = "java_library"

  def __init__(self, **kwargs):
     rule.Rule.__init__(self, kwargs["name"], package.currentPackage) 
     self.srcsList = kwargs["srcs"]
     if "deps" in kwargs:
       self.depsList = kwargs["deps"]
     else:
       self.depsList = []
     self.depRulesList = []
     self.package.addRule(self)
     self.is_library = 1
     self.emited = False

  def dump(self):
    print "\trule: ", self.ruleName
    for src in self.srcsList:
      print "\t\t", src
    for rule in self.depRulesList:
      print "\t\tdeps on: %s" % rule.ruleName


  def libraryName(self):
    return "lib%s.jar" % self.ruleName.lower();

  def makeTargetName(self, opt = 0):
    return os.path.join("build", self.package.packageName, self.libraryName())

  def makeDependsList(self):
    depStr = self.makeSrcList()
    for dep in self.depRulesList:
      depStr = "%s %s" % (depStr, dep.makeTargetName())
    return depStr

  def libraryPath(self):
    return self.makeTargetName()

  def makeSrcList(self):
    srcList = ""
    for src in self.srcsList:
      if srcList == "":
        srcList = os.path.join(self.package.packageName, src)
      else:
        srcList = "%s %s" % (srcList, os.path.join(self.package.packageName, src))
    return srcList

  def javacClassPathList(self):
    classPath = ""
    for dep in self.depRulesList:
      if classPath == "":
        classPath = dep.javaClassPathList()
      else:
        classPath = "%s:%s" % (classPath, dep.javaClassPathList())
    return classPath

  def javaClassPathList(self):
    if self.javacClassPathList() == "":
      return self.libraryPath()
    else:
      return "%s:%s" % (self.javacClassPathList(), self.libraryPath())

  def classRoot(self):
    return os.path.join("build/%s" % self.package.packageName, "classes")

  def classDir(self):
    return os.path.join(self.classRoot(), self.package.realPackageName())

  def emitMake(self, f):
    if self.emited:
      return
    self.emitSelfMake(f)
    # Emit deps rule make
    for dep in self.depRulesList:
      dep.emitMake(f)

    self.emited = True

  def emitSelfMake(self, f):
    """
     This rule generate make rules to generate jar
    """
    print >>f, "%s : %s" % (self.makeTargetName(), self.makeDependsList())
    # Emit commands
    print >>f, "\t@rm -rf %s" % self.classDir()
    print >>f, "\t@mkdir -p %s" % self.classDir()

    for srcFile in self.makeSrcList().split(" "):
      if srcFile.strip():
        print >>f, '\t@echo "_____compiling %s"' % srcFile.strip()

    if self.javacClassPathList().strip() == "":
      print >>f, "\t@$$JAVA_HOME/bin/javac -d %s %s" % (self.classRoot(),
				                        self.makeSrcList())
    else:
      print >>f, "\t@$$JAVA_HOME/bin/javac -cp %s -d %s %s" % (self.javacClassPathList(),
                                                               self.classRoot(),
				                               self.makeSrcList())
    print >>f, '\t@echo "_____linking [%s]"'% self.libraryPath()
    print >>f, "\t@$$JAVA_HOME/bin/jar cf %s -C %s %s" % (self.libraryPath(),
							  self.classRoot(),
							  self.package.packageRoot())
    print >>f, "\n"
  
   
class JavaBinary(JavaLibrary):
  """
    java_binary(name = "",
                srcs = ["",""],
                deps = ["", ""]
                )
  """
  buildName = "java_binary"

  def __init__(self, **kwargs):
    JavaLibrary.__init__(self, **kwargs)
    if "javaops" in kwargs:
      self.javaops = kwargs["javaops"]
    else:
      self.javaops = []
    self.is_binary = 1

  def startShellName(self):
    return os.path.join("build/%s" % self.package.packageName, self.ruleName)
  
  def mainClass(self):
    return os.path.join(self.package.realPackageName(), self.ruleName)

  def deployTarget(self):
    return os.path.join("build", self.package.packageName, "%s_deploy.jar" % self.ruleName)
 
  def deployName(self):
    return "%s_deploy" % self.ruleName

  def deployDir(self):
    return os.path.join("build", self.package.packageName, "deploy")

  def javaOps(self):
    ops = "";
    for op in self.javaops:
      ops += op + " "
    return ops

  def emitMake(self, f):
    # Print to start shell script
    if self.emited:
      return
    print >>f, "%s : %s" % (self.ruleName, self.makeTargetName())
    print >>f, '\t@echo "_____linking [%s]"' % self.mainClass()
    print >>f, '\t@echo "$$JAVA_HOME/bin/java %s -cp %s %s"\' $$@\' > %s; chmod u+x %s' % (
               self.javaOps(),
               self.javaClassPathList(),
	       self.mainClass(),
	       self.startShellName(),
	       self.startShellName())
    print >>f, "\n"
    # Emit deploy rule
    print >>f, "%s : %s" % (self.deployName(), self.deployTarget())
    print >>f, "%s : %s" % (self.deployTarget(), self.makeTargetName())
    print >>f, '\t@echo "_____linking %s"' % self.deployTarget()
    print >>f, '\t@rm -rf %s' % self.deployDir()
    print >>f, "\t@mkdir -p %s" % self.deployDir()
    # jar xf javaclasspath to deploy dir
    # actually we use unzip to extract jar
    jarList = self.javaClassPathList().split(":")
    for jar in jarList:
      print >>f, '\t@echo "_____unzip %s"' % jar
      print >>f, "\t@unzip -oq %s -d %s" % (jar, self.deployDir())
      print >>f, "\t@rm -f %s/META-INF/MANIFEST.MF" % self.deployDir()
      print >>f, "\t@rm -f %s/META-INF/*.SF" % self.deployDir()
      print >>f, "\t@rm -f %s/META-INF/*.DSA" % self.deployDir()
    # make manifest file, manifest include the main class
    print >>f, '\t@echo "Main-Class: %s" > %s' % (self.mainClass(),
                                                os.path.join(self.deployDir(), "META-INF", "MANIFEST.MF")) 
    # update deploy jar
    print >>f, '\t@echo "packing"'
    print >>f, "\t@chmod 755 -R %s" % self.deployDir()
    print >>f, "\t@$$JAVA_HOME/bin/jar cmf %s %s -C %s ." % (
                  os.path.join(self.deployDir(), "META-INF", "MANIFEST.MF"),
                  self.deployTarget(),
                  self.deployDir())
    print >>f, "\n"
    # Emit self package  
    JavaLibrary.emitSelfMake(self, f)
    # Emit deps make
    for dep in self.depRulesList:
      dep.emitMake(f)

    self.emited = True

class JavaProto(JavaLibrary):
  """
    java_proto(name = "",
               srcs = [""],
              )
  """
  buildName = "java_proto"
 
  def __init__(self, **kwargs):
     JavaLibrary.__init__(self, **kwargs) 
		       
  def genJavaFile(self, protoFile):
    return "%s.java" % protoFile[:-6]

  def emitMake(self, f):
     if self.emited:
       return;
      
     javaList = []
     for src in self.srcsList:
       print >>f, "%s/%s : %s/%s" % (self.package.packageName, self.genJavaFile(src), self.package.packageName, src)
       print >>f, '\t@echo "_____generate java proto [%s]"' % src 
       print >>f, "\t@third_party/bin/protoc --java_out=java/ -I./ %s/%s " % (self.package.packageName, src) 
       javaList.append(self.genJavaFile(src))
     print >>f, "\n"

     # compile java to class
     self.srcsList = javaList
     JavaLibrary.emitMake(self, f)

     self.emited = True

class JavaLib(JavaLibrary):
  """
    java_lib(name = "",
             srcs = ["", ""]
            )
  """
  buildName = "java_lib"
  def __init__(self, **kwargs):
     JavaLibrary.__init__(self, **kwargs)

  def dump(self):
    print "\trule:", self.ruleName
    for src in self.srcsList:
      print "\t\t", src

  def makeTargetName(self, opt = 0):
    return os.path.join("build", self.package.packageName, "%s.stamp" % self.ruleName)
  
  def libraryPath(self):
    libPath = ""    
    for src in self.srcsList:
      if libPath == "":
        libPath = os.path.join(self.package.packageName, src)
      else:
        libPath = "%s:%s" % (libPath, os.path.join(self.package.packageName, src))
    return libPath

  def emitMake(self, f):
    if self.emited:
      return
    print >>f, "%s : %s" % (self.makeTargetName(), self.makeSrcList())
    print >>f, '\t@echo "_____make lib [%s]"' % self.ruleName
    print >>f, "\t@mkdir -p %s" % os.path.join("build", self.package.packageName)
    print >>f, "\t@touch %s" % self.makeTargetName()
    print >>f, "\n"

    self.emited = True

class JavaData(JavaLibrary):
  """
    java_data(name= "",
              srcs = [""],
             )
  """
  buildName = "java_data"
  def __init__(self, **kwargs):
     JavaLibrary.__init__(self, **kwargs)

  def dump(self):
    print  "\t", self.ruleName, self.srcsList

  def emitMake(self, f):
    if self.emited:
      return
    print >>f, "%s : %s" % (self.makeTargetName(), self.makeSrcList())
    print >>f, '\t@echo "_____make data [%s]"' % self.ruleName
    print >>f, "\t@mkdir -p %s" % os.path.join("build", self.package.packageName)
    print >>f, "\t@$$JAVA_HOME/bin/jar cf %s %s" % (self.libraryPath(),
					            self.makeSrcList())

    self.emited = True
