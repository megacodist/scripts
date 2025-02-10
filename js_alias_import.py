#
# This command-line utility is used to replace aliases in absolute import
# statements of provided file types, typically and default to JS, with
# provided paths.
#

import argparse
from functools import partial
import os
from pathlib import Path
import re
from re import Match, Pattern
import sys
from typing import Iterable, Mapping


class STRS:
    APP_DESCR = 'Replace aliases in absolute import statements with provided paths.'
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
    FINDING_IMPORT_ALAIASES = 'Finding import aliases in {}...'
    REPLACEMENTS_REPORTS = 'Changes in {}:'
    REPLACEMENT = '\t{} -> {}'


_PATTERN = r'''
    import
    \s+.*?\s+
    from
    \s+
    ['"]
    (?P<alias>{aliases})
    /                     # Alias should be at the start of the path
    (?P<relPath>.*?)      # Capturing the relative path
    ['"]
'''

def replaceMatch(
        changes: list[str],
        mp_alias_path: Mapping[str, str],
        match: Match[str],
        ) -> str:
    fullMatch = match.group(0)
    # Changing the alias...
    alias = match.group('alias')
    try:
        path = mp_alias_path[alias]
    except KeyError:
        # Doing nothing if alias is not present in tha mapping...
        return fullMatch
    fullMatch = fullMatch.replace(alias, path)
    changes.append(alias)
    # Changing the relative path...
    relPath = Path(match.group('relPath'))
    if relPath.suffix.lower() not in _KNOWN_EXTS:
        newRelPath = relPath.with_suffix('.js')
        fullMatch = fullMatch.replace(str(relPath), str(newRelPath))
    return fullMatch


_KNOWN_EXTS = ['.json', '.js']
"""Known extensions that should not be changes."""


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
    global _PATTERN
    aliases = '|'.join(map(re.escape, mp_alias_path.keys()))
    pattern = _PATTERN.format(aliases=aliases)
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
    print(file)
    msg = STRS.FINDING_IMPORT_ALAIASES.format(file)
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
        description=STRS.APP_DESCR,)
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
    print('Replacements:')
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
