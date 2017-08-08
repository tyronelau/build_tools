#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'liuyong@agora.io(Yong Liu)'

import re
import sys, os
import package

"""
Rule is defined in package's build file
For example:
cc_library(name = "test",
     srcs = ["test.cc", "test_impl.cc"],
             deps = [
                      "//packagename/BUILD:rulename",
                      ]
             )
This define a cpp library rule. Its name is test, so it will generates libtest.a
libtest.a includes test.o and test_impl.o, it depends on packagename:rulename,
this means that to compile libtest.a, packagename:rulename must be generate first 

cc_binary(name = "binary",
            srcs = ["binary.cc"],
      deps = ["//packagename/BUILD:rulename",
        ":test"]
           )
This defines a cpp binary rules. it will generate binary which contains binary.o
"""

class Rule:

  ruleExpandStack = []

  def __init__(self, name, pkg):
     # deps rule format is: //packageName/BUILD:ruleName or :ruleName, second is the rule in same package
     self.ruleRegex = re.compile(r'''/?/?(.*?):(.+)''', re.IGNORECASE)
     self.ruleName = name
     self.srcList = []
     self.package = pkg
     self.expanded = False

     self.is_binary = 0
     self.is_unittest = 0  # for a unit test executable, both is_unittest and is_binary should be 1
     self.is_proto = 0
     self.is_library = 0
     self.is_pyext = 0
     self.is_mpi = 0
     self.is_data = 0
     self.is_shell_script = 0
     self.is_script_test = 0
     self.is_jni_used = 0

     self.is_dummy_lib = 0  # a lib without any cc, useful to expos public .h only and hide all implementations

  def expandRule(self):
    """
     1. for each depending rule, create its package if not exist, and create each rule, add to depRulesList
     2. check for circly depending
        birth first way to expand the rule graph
     3. for echo depending rule, expand it
    """
    print "parse module: //%s/BUILD:%s" % (self.package.packageName, self.ruleName)

    self.pushStack()
    for dep in self.depsList:
      packageName, ruleName = self.parseRule(dep)
      if packageName == None and ruleName == None:
        print >>sys.stderr, "depends: %s is not valid" %dep
        sys.exit(1)

      if ruleName == None:
        print "please specify the rule name at %s" % dep
        sys.exit(1)

      # Get package object
      pkg = None
      if packageName == "":
        pkg = self.package
      else:
        if packageName in package.globalPackages:
          pkg = package.globalPackages[packageName]
        else:
          # will add the package to globalPackages map, and create package' rules
          pkg = package.Package.createPackage(packageName, self.package.dirPrefix)
      if pkg == None:
        print "package: %s does not exist" % packageName
        sys.exit(1)
      # Get rule
      rule = pkg.getRule(ruleName)
      if rule == None:
        print
        print "module not found: //%s/BUILD:%s, used in deps of //%s/BUILD:%s" \
            % (pkg.packageName, ruleName, self.package.packageName, self.ruleName)
        sys.exit(1)
      self.depRulesList.append(rule)

    # Expand dep rules
    for rule in self.depRulesList:
      if rule.fullRuleName() in Rule.ruleExpandStack:
        print "%s -> %s -> %s,  circly dependency error" % (self.fullRuleName(), rule.fullRuleName(), self.fullRuleName())
        self.popStack()
        sys.exit(1)
      if not rule.expanded:
        rule.expandRule()

    # Pop out from expend stack
    self.popStack()
    self.expanded = True

  def fullRuleName(self):
    return "%s:%s" % (self.package.packageName, self.ruleName)

  def pushStack(self):
    Rule.ruleExpandStack.append(self.fullRuleName())

  def popStack(self):
    Rule.ruleExpandStack.pop()

  def parseRule(self, dep):
    if not dep.startswith("//") and not dep.startswith(":"):
      print 'invalid deps: "%s"' % dep
      print 'must be started with "//" (means in the codebase root dir) or ":" (means in the current package)'
      sys.exit(-1)
    ruleMatcher = self.ruleRegex.match(dep)
    if ruleMatcher == None:
      return [None, None]
    packageName = ruleMatcher.group(1).strip()
    ruleName = ruleMatcher.group(2).strip()

    if len(packageName) > 0:
      if not packageName.endswith("/BUILD"):
        print "invalid deps: %s" % dep
        print "please specify BUILD file path in deps of //%s/BUILD:%s" % (self.package.packageName, self.ruleName)
        sys.exit(-1)
      packageName = packageName[:-6]

    return [packageName, ruleName]

  def emitMake(self, f):
    pass
