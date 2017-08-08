#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'liuyong@agora.io(Yong Liu)'

import java
import cc
import data
import shell
import genrule

rules = [
         cc.CCLibrary,
         cc.CCBinary,
         cc.CCJNILibrary,
         cc.CCMPILibrary,
         cc.CCMPIBinary,
         cc.CCTest,
         cc.CCPyExt,
         data.CCData,
         shell.ShellScript,
         shell.SSTest,
         genrule.ProtoLibrary,
         genrule.SetPackageAttr,
        ]

def insertIntoContext(context):
  for rule in rules:
    context[rule.buildName] = rule
