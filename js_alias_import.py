#
# This command-line utility is used to replace aliases in absolute import
# statements of provided file types, typically and default to JS, with
# provided paths.
#

import argparse
import datetime
from functools import partial
import os
from pathlib import Path, PurePosixPath
import re
from re import Match, Pattern
import sys
from typing import Iterable, Mapping


class STRS:
    DEV = 'Megacodist'
    APP_NAME = f'{DEV} JS Alias Import Replacer'
    VERSION = f'{APP_NAME} v1.1.0'
    COPYWRITE = '@2021-{year} {dev}. This app is available under MIT License.'
    APP_DESCR = 'Replace aliases in absolute import-from statements with provided paths.'
    DIR_HELP = 'Directory to look for files, defaults to the current directory.'
    NO_SUB_DIRS_HELP = "Do not process subdirectories (default: process subdirectories)"
    EXTS_HELP = 'Space-separated list of file extensions to process like js or "js ts". It is default to `js` files.'
    ALIAS_HELP = 'One or more aliases to replace. Use one or more alias like --alias "@utils /path/replacement/"'
    DIR_PRMPT_NO_SUB_DIRS = 'Directory: {} (no sub-folders)'
    DIR_PRMPT_SUB_DIRS = 'Directory: {} (sub-folders included)'
    EXTS_PRMPT = 'Looking for files with extensions: {}'
    CONFR = 'Enter Y to apply changes:'
    USER_CANCELED = 'Operation cancelled by user.'
    DUP_ALIASES = 'Duplicate alias `{}` found. Aliases must be unique.'
    SEARCHING_IMPORT_FROM_ALAIAS = '>> Searching for import-from alias in "{}"...'
    REQ_REPLACEMENTS = 'Requested replacements:'
    REPLACEMENTS_REPORTS = 'Changes in "{}":'
    REPLACEMENT = '\t{} -> {}'


_IMPORT_FROM_ALIAS_PATT = r'''
    \bimport\b
    \s+
    (?P<stuff>(?:(?!\s+from\b).)*?) # Capturing anything but not `from`
    \s+from\b
    \s+
    (['"])                     # Capturing the opening quote
    (?P<alias>{aliases})       # Capturing the alias
    (?P<relPath>(?:/[^'"]+)+?) # Capturing the relative path
    \2                         # Matching the closing quote
'''

def replaceMatch(
        changes: list[str],
        mp_alias_path: Mapping[str, str],
        match: Match[str],
        ) -> str:
    # Reading parts of the import-from statement...
    stuff = match.group('stuff')
    alias = match.group('alias')
    relPath = match.group('relPath')
    quote = match.group(2)
    # Checking if the alias is in the mapping...
    try:
        pthAlias = PurePosixPath(mp_alias_path[alias])
    except KeyError:
        # Doing nothing bacause alias is not present in tha mapping...
        return match.group(0)
    else:
        changes.append(alias)
    # Changing the alias & the relPath...
    alias = str(pthAlias)
    pthRelPath = PurePosixPath(relPath)
    if pthRelPath.suffix.lower() not in _KNOWN_EXTS:
        pthRelPath = pthRelPath.with_suffix('.js')
    relPath = str(pthRelPath)
    # Returning the updated import-from statement...
    return f'import {stuff} from {quote}{alias}{relPath}{quote}'


_KNOWN_EXTS = ['.json', '.js']
"""Known extensions that should not be changed."""


def _searchFiles(
        dir: str,
        exts: Iterable[str],
        mp_alias_path: Mapping[str, str],
        include_subdirs: bool =True,
        ) -> None:
    """Searches in `dir` folder and all its subfolders if
    `include_subdirs` is provided for all files with any extension
    provided in `exts` to replace their import aliases with the paths
    in `replacements`.
    """
    # Declaring variables...
    global _IMPORT_FROM_ALIAS_PATT
    aliases = '|'.join(map(re.escape, mp_alias_path.keys()))
    pattern = _IMPORT_FROM_ALIAS_PATT.format(aliases=aliases)
    regex = re.compile(pattern, re.DOTALL | re.VERBOSE)
    # Searching the directory...
    pthDir = Path(dir)
    dirsIter = pthDir.rglob('*') if include_subdirs else pthDir.glob('*')
    for pthFile in dirsIter:
        if pthFile.is_file() and pthFile.suffix.lstrip('.') in exts:
            _replaceAliases(pthFile, regex, mp_alias_path)


def _replaceAliases(
        file: Path,
        regex: Pattern[str],
        mp_alias_path: Mapping[str, str],
        ) -> None:
    """Searches the `file` against the provided `regex` and replaces any
    matched alias with the path in `mp_alias_path`.
    """
    # Declaring stuff...
    changes = list[str]()
    replacer = partial(replaceMatch, changes, mp_alias_path)
    # Prompting the user...
    msg = STRS.SEARCHING_IMPORT_FROM_ALAIAS.format(file)
    sys.stdout.write(msg)
    sys.stdout.flush()
    # Finding import aliases & replacing them...
    content = file.read_text()
    updatedContent = regex.sub(replacer, content)
    # Clearing previous message...
    sys.stdout.write("\r" + " " * len(msg) + "\r")
    sys.stdout.flush()
    # 
    if content != updatedContent:
        print(STRS.REPLACEMENTS_REPORTS.format(file))  
        for alias in changes:
            print(STRS.REPLACEMENT.format(alias, mp_alias_path[alias]))
        file.write_text(updatedContent)


def main():
    # Defining flags...
    parser = argparse.ArgumentParser(
        prog=STRS.APP_NAME,
        description=STRS.APP_DESCR,
        epilog=STRS.COPYWRITE.format(
            year=datetime.date.today().year,
            dev=STRS.DEV))
    parser.add_argument(
        '-v',
        '--version',
        action='version',
        version=STRS.VERSION)
    parser.add_argument(
        '--dir',
        default=os.getcwd(),
        help=STRS.DIR_HELP,)
    parser.add_argument(
        '--no-sub-dirs',
        action='store_true',
        default=False,
        help=STRS.NO_SUB_DIRS_HELP,)
    parser.add_argument(
        '--exts',
        default='js',
        help=STRS.EXTS_HELP,)
    parser.add_argument(
        '--alias',
        action='append',
        type=str,
        required=True,
        help=STRS.ALIAS_HELP,)
    # Getting falgs from the user...
    args = parser.parse_args()
    # Creating extensions list from args...
    extensions: list[str] = [
        ext.strip() for ext in args.exts.split() if ext.strip()]
    # Creating replacements dictionary from args for easy lookup...
    # Ensuring no slash after aliases...
    # Ensuring paths start with one slash, no trailing slashes...
    mpAliasPath: dict[str, str] = {}
    aliases = set[str](args.alias)
    for alias in aliases:
        pair = alias.split(maxsplit=1)
        key = pair[0].rstrip('/')
        value = '/' + pair[1].strip('/')
        if key in mpAliasPath:
            print(STRS.DUP_ALIASES.format(key))
            return
        mpAliasPath[key] = value
    # Prompting `dir` & `no_sub_dirs`...
    msg = STRS.DIR_PRMPT_NO_SUB_DIRS.format(args.dir) if args.no_sub_dirs \
        else STRS.DIR_PRMPT_SUB_DIRS.format(args.dir)
    print(msg)
    # Prompting `extensions`...
    msg = STRS.EXTS_PRMPT.format(', '.join(extensions))
    print(msg)
    # Prompting `replacements`...
    print(STRS.REQ_REPLACEMENTS)
    for alias, path in mpAliasPath.items():
        print(STRS.REPLACEMENT.format(alias, path))
    # Prompting user for confirmation...
    confr = input(STRS.CONFR).lower()
    if confr != 'y':
        print(STRS.USER_CANCELED)
        sys.exit(0)
    #
    _searchFiles(args.dir, extensions, mpAliasPath, not args.no_sub_dirs)


if __name__ == '__main__':
    main()
