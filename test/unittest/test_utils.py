# Copyright 2013-2014 Sebastian Kreft
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os.path
import unittest
import sys

import mock
from pyfakefs import fake_filesystem_unittest

import gitlint.utils as utils

# pylint: disable=too-many-public-methods,protected-access


def _mock_abspath(filename):
    if os.path.isabs(filename):
        return filename
    return '/foo/%s' % filename


class UtilsTest(fake_filesystem_unittest.TestCase):
    def setUp(self):
        self.setUpPyfakefs()

    def test_filter_lines_no_groups(self):
        lines = ['a', 'b', 'c', 'ad']
        self.assertEqual(lines, list(utils.filter_lines(lines, '.')))
        self.assertEqual(['a', 'ad'], list(utils.filter_lines(lines, 'a')))
        self.assertEqual(['ad'], list(utils.filter_lines(lines, '.d')))
        self.assertEqual(['ad'], list(utils.filter_lines(lines, 'd')))
        self.assertEqual([], list(utils.filter_lines(lines, '^d')))
        self.assertEqual([], list(utils.filter_lines(lines, 'foo')))

    def test_filter_lines_one_group(self):
        lines = ['1: foo', '12: bar', '', 'Debug: info']
        self.assertEqual(['1', '12'],
                         list(
                             utils.filter_lines(
                                 lines,
                                 r'(?P<line>\d+): .*',
                                 groups=('line', ))))

    def test_filter_lines_many_groups(self):
        lines = ['1: foo', '12: bar', '', 'Debug: info']
        self.assertEqual([('1', 'foo'), ('12', 'bar')],
                         list(
                             utils.filter_lines(
                                 lines,
                                 r'(?P<line>\d+): (?P<info>.*)',
                                 groups=('line', 'info'))))
        self.assertEqual([('1', 'foo', ':'), ('12', 'bar', ':')],
                         list(
                             utils.filter_lines(
                                 lines,
                                 r'(?P<line>\d+)(?P<separator>:) (?P<info>.*)',
                                 groups=('line', 'info', 'separator'))))

    def test_filter_lines_group_not_always_defined(self):
        lines = ['1: foo', '12: bar', '', 'Debug: info']
        self.assertEqual([('1', None), ('12', None), (None, 'info')],
                         list(
                             utils.filter_lines(
                                 lines,
                                 r'(?P<line>\d+): .*|Debug: (?P<debug>.*)',
                                 groups=('line', 'debug'))))

    def test_filter_lines_group_not_defined(self):
        lines = ['1: foo', '12: bar', '', 'Debug: info']
        self.assertEqual([('1', None), ('12', None)],
                         list(
                             utils.filter_lines(
                                 lines,
                                 r'(?P<line>\d+): .*',
                                 groups=('line', 'debug'))))

    @unittest.skipUnless(sys.version_info >= (3, 5),
                         'pyfakefs does not support pathlib2. See'
                         'https://github.com/jmcgeheeiv/pyfakefs/issues/408')
    def test_open_for_write(self):
        filename = 'foo/bar/new_file'
        with utils._open_for_write(filename) as f:
            f.write('foo')
        with open(filename) as f:
            self.assertEqual('foo', f.read())

    @mock.patch('os.path.abspath', side_effect=_mock_abspath)
    @mock.patch('os.path.expanduser', side_effect=lambda a: '/home/user')
    def test_get_cache_filename(self, _, __):  # pylint: disable=invalid-name
        # pylint: disable=line-too-long
        self.assertEqual(
            '/home/user/.git-lint/cache/e847a69549b9413ce543dfc2a08a26aa2fc76b41',
            utils._get_cache_filename('linter1', 'lint1', {}, 'bar/file.txt'))

        self.assertEqual(
            '/home/user/.git-lint/cache/71262e3079c8f3a3133f9bc5c0f4740bd3db3e2f',
            utils._get_cache_filename('linter2', 'lint2', {}, 'file.txt'))

        self.assertEqual(
            '/home/user/.git-lint/cache/466b0918b56b96a47446546e4cbe15019022666c',
            utils._get_cache_filename('linter3', 'lint3', {}, '/bar/file.txt'))

    @mock.patch('os.path.abspath', side_effect=_mock_abspath)
    @mock.patch('os.path.expanduser', side_effect=lambda a: '/home/user')
    def test_cache_name_change(self, _, __):  # pylint: disable=invalid-name
        """ Make sure file name changes when program name or arguments change
        """
        result1 = utils._get_cache_filename('linter', 'lint1', {}, 'file.txt')
        result2 = utils._get_cache_filename('linter', 'lint2', {}, 'file.txt')
        result3 = utils._get_cache_filename('linter', 'lint1',
                                            {'args': [1, 2, 3]}, 'file.txt')
        result4 = utils._get_cache_filename('linter', 'lint2', {}, 'file.txt')

        self.assertNotEqual(result1, result2)
        self.assertNotEqual(result1, result3)
        self.assertNotEqual(result2, result3)
        self.assertEqual(result2, result4)

    @unittest.skipUnless(sys.version_info >= (3, 5),
                         'pyfakefs does not support pathlib2. See'
                         'https://github.com/jmcgeheeiv/pyfakefs/issues/408')
    def test_save_output_in_cache(self):
        output = 'Some content'
        cache_filename = '/cache/filename.txt'
        mock_file = mock.MagicMock()
        with mock.patch('gitlint.utils._get_cache_filename',
                        return_value=cache_filename), \
             mock.patch('gitlint.utils._open_for_write',
                        mock.mock_open(mock_file)) as mock_open:
            utils.save_output_in_cache('linter', 'lint', {}, 'filename',
                                       output)
            mock_open.assert_called_once_with(cache_filename)
            mock_file().write.assert_called_once_with(output)

    def test_get_output_from_cache_no_cache(self):
        cache_filename = '/cache/filename.txt'
        with mock.patch(
                'gitlint.utils._get_cache_filename',
                return_value=cache_filename):
            self.assertIsNone(
                utils.get_output_from_cache('linter', 'lint', {}, 'filename'))

    def test_get_output_from_cache_cache_is_expired(self):
        cache_filename = '/cache/filename.txt'
        self.fs.create_file(cache_filename)
        self.fs.create_file('filename')
        with mock.patch(
                'gitlint.utils._get_cache_filename',
                return_value=cache_filename):
            self.assertIsNone(
                utils.get_output_from_cache('linter', 'lint', {}, 'filename'))

    def test_get_output_from_cache_cache_is_valid(self):
        cache_filename = '/cache/filename.txt'
        content = 'some_content'
        with mock.patch('gitlint.utils._get_cache_filename',
                        return_value=cache_filename), \
             mock.patch('os.path.exists', return_value=True), \
             mock.patch('os.path.getmtime', side_effect=[1, 2]), \
             mock.patch('io.open',
                        mock.mock_open(read_data=content),
                        create=True) as mock_open:
            self.assertEqual(
                content,
                utils.get_output_from_cache('linter', 'lint', {}, 'filename'))
            mock_open.assert_called_once_with(cache_filename)

    def test_which_absolute_path(self):
        filename = '/foo/bar.sh'
        self.fs.create_file(filename)
        os.chmod(filename, 0o755)

        self.assertEqual([filename], utils.which(filename))
