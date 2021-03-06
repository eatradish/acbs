#!/bin/env python
import os
import re
import logging

'''
ACBS Search
'''


class Finder(object):

    def __init__(self, target, search_path=None):
        self.target = target
        self.path = search_path or os.path.abspath('.')

    def acbs_pkg_match(self):
        logging.debug('Search Path: %s' % self.path)
        if self.target.startswith('groups') and os.path.isfile(os.path.join(self.path, self.target)):
            with open(os.path.join(self.path, self.target), 'rt') as cmd_list:
                pkg_list_str = cmd_list.read()
            pkg_list = pkg_list_str.splitlines()
            group_pkg = []
            for pkg in pkg_list:
                if not pkg.strip():
                    continue
                match_res = self.acbs_pkg_match_core(target=pkg)
                if match_res is not None:
                    group_pkg.append(match_res)
                else:
                    logging.warning('Package %s not found!' % pkg)
            logging.debug('Packages to be built: %s' % ', '.join(group_pkg))
            return group_pkg
        else:
            return self.acbs_pkg_match_core()

    def acbs_pkg_match_core(self, target=None):
        if target is None:
            target = self.target
        if os.path.isdir(target):
            return os.path.relpath(target, self.path)
        target_slug = target.split('/')
        if len(target_slug) > 1:
            _, target = target_slug
        for path in os.listdir(self.path):
            secpath = os.path.join(self.path, path)
            if not (os.path.isdir(secpath)):
                continue
            for pkgpath in os.listdir(secpath):
                if pkgpath == target and os.path.isdir(os.path.join(secpath, pkgpath)):
                    return os.path.relpath(os.path.join(secpath, pkgpath), self.path)

    def acbs_verify_pkg(self, path, strict_mode=False):
        if os.path.exists(os.path.join(path, 'spec')):
            if strict_mode and not os.path.exists(os.path.join(path, 'autobuild/defines')):
                raise Exception('Can\'t find `defines` file!')
        else:
            raise Exception(
                'Candidate package\033[93m {} \033[0mdoesn\'t seem to be valid!'.format(path))
