import subprocess
import os
from urllib import parse
import logging
import shutil

from acbs.loader import LoaderHelper
from acbs.vcs import VCS


class SourceFetcher(object):

    def __init__(self, pkg_name, pkg_info, dump_loc='/var/cache/acbs/tarballs/'):
        self.pkg_name = pkg_name
        self.pkg_info = pkg_info
        self.dump_loc = dump_loc
        self.ind_dump_loc = os.path.join(self.dump_loc, self.pkg_name)

    def fetch_src(self):
        if self.pkg_info.get('DUMMYSRC'):
            logging.info('Not fetching dummy source as required.')
            return
        if self.pkg_info.get('SRCTBL'):
            return self.src_url_dispatcher()
        for src in ('SRCTBL', 'GITSRC', 'SVNSRC', 'HGSRC', 'BZRSRC'):
            if self.pkg_info.get(src):
                if src == 'SRCTBL':
                    return self.src_tbl_fetch(self.pkg_info[src])
                if src in ('GITSRC', 'SVNSRC', 'HGSRC', 'BZRSRC'):
                    self.vcs_dispatcher(
                        self.pkg_info[src], src_type=src[:-3].lower())
                    return self.pkg_name
        raise Exception('No source URL specified?!')

    def src_url_dispatcher(self):
        url = self.pkg_info.get('SRCTBL')
        # url_array = url.split('\n').split(' ') #for future usage
        pkg_name = self.pkg_name
        pkg_ver = self.pkg_info['VER']
        try:
            proto, _, _, _, _, _ = parse.urlparse(url)
            # Some of the varibles maybe used in the future, now leave them
            # as placeholder
        except Exception as ex:
            raise ValueError('Illegal source URL!!!') from ex
        if proto in ('http', 'https', 'ftp', 'ftps', 'ftpes'):
            src_tbl_name = '%s-%s.bin' % (pkg_name, pkg_ver)
            self.src_tbl_fetch(url, src_tbl_name)
            return src_tbl_name
        else:  # or proto == 'git+https'
            logging.warning(
                'In spec file: This source seems to refers to a VCS repository, but you misplaced it.')
            self.vcs_dispatcher(url)
            return pkg_name

    def src_tbl_fetch(self, url, pkg_slug=None):
        use_progs = self.test_downloaders()
        src_name = pkg_slug or os.path.basename(url)
        full_path = os.path.join(self.dump_loc, src_name)
        flag_file = full_path + '.dl'
        if os.path.exists(full_path) and (not os.path.exists(flag_file)):
            return
        with open(flag_file, 'wt') as flag:
            flag.write('acbs flag: DO NOT DELETE!')
        for i in use_progs:
            try:
                getattr(self, i + '_get')(url=url, output=full_path)
                os.unlink(flag_file)
                break
            except KeyboardInterrupt as ex:
                raise KeyboardInterrupt('You aborted the download!') from ex
            except NameError:
                raise NameError('An Internal Error occurred!')
            except AssertionError as ex:
                raise ex
            except Exception as ex:
                raise Exception('Something happend!') from ex

    def vcs_dispatcher(self, url, src_type=None):
        logging.debug('Sending to VCS module:{} URL:{}'.format(src_type, url))
        self.__register_vcs_checkout(url, src_type)
        VCS(url=url, repo_dir=os.path.join(self.dump_loc,
                                           self.pkg_name), proto=src_type).vcs_fetch_src()

    def __register_vcs_checkout(self, url, src_type):
        @LoaderHelper.register('before_copy_defines', (self, url, src_type))
        def vcs_checkout(self, url, src_type):
            old_loc = os.path.abspath(os.path.curdir)
            os.chdir(self.pkg_name)
            VCS(url=url, repo_dir=os.path.join(self.dump_loc,
                                               self.pkg_name), proto=src_type).vcs_checkout(commit=self.pkg_info.get(src_type.upper() + 'CO'), branch=self.pkg_info.get(src_type.upper() + 'BRCH'))
            os.chdir(old_loc)

    '''
    External downloaders
    '''

    def test_downloaders(self):
        use_progs = []
        if shutil.which('wget'):
            use_progs.append('wget')
        if shutil.which('axel'):
            use_progs.append('axel')
        return use_progs

    def axel_get(self, url, threads=4, output=None):
        axel_cmd = ['axel', '-n', threads, '-a', url]
        if output:
            axel_cmd.insert(4, '-o')
            axel_cmd.insert(5, output)
        try:
            subprocess.check_call(axel_cmd)
        except Exception:
            raise AssertionError('Failed to fetch source with Axel!')

    def wget_get(self, url, output):
        wget_cmd = ['wget', '-c', url]  # ,'--no-check-certificate'
        if output:
            wget_cmd.insert(2, '-O')
            wget_cmd.insert(3, output)
        try:
            subprocess.check_call(wget_cmd)
        except Exception:
            raise AssertionError('Failed to fetch source with Wget!')
