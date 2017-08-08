#!/usr/bin/env python
__author__ = 'liuyong@agora.io(Yong Liu)'

import package as p
import rule
import sys
import os

def main(argv):
  package_set = set()
  for packageName in argv[1:]:
    packageName = packageName.strip()
    if packageName.startswith("/") or packageName.startswith("../"):
      print >> sys.stderr, "Invalid BUILD file, not a relative path: ", \
          packageName
      sys.exit(-1)

    if packageName.startswith("./"): packageName = packageName[2:]

    if not packageName.endswith("/BUILD"):
      print >> sys.stderr, "not a BUILD file: ", packageName
      print >> sys.stderr, "please specify a path to a BUILD file"
      sys.exit(-1)

    if packageName in package_set:
      print >> sys.stderr, "repeated BUILD file: " + packageName
      sys.exit(-1)
    package_set.add(packageName)

  dirPrefix = os.getcwd()
  packages = []

  for packageName in argv[1:]:
    packageName = packageName.strip()
    if packageName.startswith("./"): packageName = packageName[2:]
    if not packageName.endswith("/BUILD"):
      print >> sys.stderr, "not a BUILD file: ", packageName
      print >> sys.stderr, "please specify a path to a BUILD file"
      sys.exit(-1)

    packageName = packageName[:-6]
    package = p.Package(packageName, dirPrefix)

    print "_____gen_makefile %s" % package.packageName

    package.readPackage()
    package.expandRules()
    packages.append(package)

  for package in p.globalPackages.values():
    package.dump()

  makeFile = open("Makefile", "w")
  p.emitMake(packages, makeFile)

if __name__ == "__main__":
  if len(sys.argv) == 1:
    print >>sys.stderr, "Please specify a package directory"
  main(sys.argv)
