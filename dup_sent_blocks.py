#
# 
#

import argparse
import platform
import sys
from typing import Literal


EOF_KEYSTROKE = 'Ctrl+' + ('Z' if platform.system() == 'Windows' else 'D')
"""The EOF keystroke in the OS."""


def _repSentBlocks(sentences: list[str], count: int) -> list[str]:
    """Repeats sentence blocks (sentences between empty strings) for the
    specified number of times.
    
    For example the algorithm receives
    
    `['a', 'b', '', 'c',]`
    
    And `count=2`, it returns:

    `['a', 'b', 'a', 'b', '', 'c', 'c',]`
    """
    repLst = list[str]()
    cpySents = [sentence.strip() for sentence in sentences]
    startIdx = 0
    while True:
        # Finding the start of a new sentence block...
        try:
            if not cpySents[startIdx]:
                startIdx += 1
                continue
        except IndexError:
            # We cold not find the start of a new sentence block.
            # Exiting the algorithm...
            break
        # Finding the end of this sentence block...
        try:
            nextIdx = cpySents.index('', startIdx + 1)
        except ValueError:
            # We could not find the next empty string.
            # So, this is the last block...
            nextIdx = len(cpySents)
        # Repeating this sentence block...
        for _ in range(count):
            repLst.extend(cpySents[startIdx:nextIdx])
        repLst.append('')
        # Getting ready for the next iteration...
        startIdx = nextIdx + 1
    return repLst


def _repLines(lines: list[str], count: int) -> list[str]:
    """Repeats each non-blank line for the specified `count` times and add
    an empty line after them.
    """
    repLst = list[str]()
    cpyLines = [line.strip() for line in lines]
    idx = 0
    while True:
        # Finding the start of a new sentence block...
        try:
            if not cpyLines[idx]:
                idx += 1
                continue
        except IndexError:
            # No more lines, exiting the algorithm...
            break
        # Repeating the current line...
        for _ in range(count):
            repLst.append(cpyLines[idx])
        repLst.append('')
        # Going to next iteration...
        idx += 1
    return repLst


def _repeat(
        text: list[str],
        level: Literal['line', 'block'],
        count: int,
        ) -> list[str]:
    """Duplicates text at the line or block level."""
    match level:
        case 'line':
            return _repLines(text, count)
        case 'block':
            return _repSentBlocks(text, count)
        case _:
            raise ValueError(f'Invalid level: {level}')


def _checkPyVer(major: int, minor: int,) -> None:
    """Checks if the Python version satisfies the following conditions,
    otherwise raises `RuntimeError`.
    1. Major number is equal to `major`.
    2. Minor number is equal to or greater than `minor`.
    """
    currMajor = sys.version_info.major
    currMinor = sys.version_info.minor
    if major == currMajor and minor <= currMinor:
        return
    else:
        raise RuntimeError(f'In compatible Python version.')


def main():
    # Checking requirements...
    try:
        _checkPyVer(3, 10)
    except RuntimeError:
        print('Python 3.10+ required.')
        sys.exit(1)
    # Defining parser...
    parser = argparse.ArgumentParser(
        description=(
            'Repeats input text at line or block level at the specified'
            ' number.'))
    parser.add_argument(
        '-l',
        '--level',
        choices=['line', 'block'],
        default='line',
        help='Repeatition level: line or block (default: line)')
    parser.add_argument(
        '-c',
        '--count',
        type=int,
        default=2,
        help='Number of times to repeat (default: 2)')
    # Getting arguments...
    args = parser.parse_args()
    print('Repetition level:', args.level)
    print('Repetition count:', args.count)
    # Getting the text...
    lines = list[str]()
    print('Enter sentences, press Ctrl+C on an empty line to signal the end:')
    try:
        for line in sys.stdin:
            lines.append(line.strip())
    except KeyboardInterrupt:
        pass
    # Processing...
    if not lines:
        print('Error: No input provided.', file=sys.stderr)
        sys.exit(1)
    lines = _repeat(lines, args.level, args.count)
    # Printing the result...
    print(' Result '.center(60, '='))
    for line in lines:
        print(line)


if __name__ == '__main__':
    main()
