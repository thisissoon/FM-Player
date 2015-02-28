#!/usr/bin/env python
# encoding: utf-8

import os

root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
version_path = os.path.join(root, '..', 'VERSION')

with open(version_path, 'r') as f:
    __version__ = unicode(f.readline().rstrip())

__author__ = 'SOON_ London'
__author_email__ = 'dorks@thisissoon.com'
