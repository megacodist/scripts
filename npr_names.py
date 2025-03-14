#
#
#

from datetime import datetime
import enum
from functools import lru_cache
from pathlib import Path
import re
import signal
import sys
from types import FrameType
from typing import Generator, Iterable, overload


class _STRS:
    DEV = 'Megacodist'
    APP_NAME = f'{DEV} NPR Name Normalizer'
    APP_DESCR = 'Normalizes the names of NPR podcast files.'
    ENTER_NPR_DIR = 'Enter the directory of NPR podcasts: '
    BAD_DIR = '\tThere is something wrong with the directory: {reason}'
    UNKNOWN_FS_ITEM = 'Unknown file system item: {item}'
    NPR_POD_DIR = 'Looking into "{dir_}":'
    RENAMED = '\t↷ {old_stem} ⇒ {new_stem}'
    NAME_OK = '\t✔ {stem}'
    BAD_NPR_NAME = '\t🞩 {stem}: {reason}'


class _NprNameParts:
    def __init__(self) -> None:
        self._parts = list[str]()
        self._dateIdx: int | None = None
    
    @property
    def dateIdx(self) -> int | None:
        """Gets the index of date field."""
        return self._dateIdx
    
    def __iter__(self) -> Iterable[str]:
        return iter(self._parts)
    
    def __eq__(self, obj: object) -> bool:
        if not isinstance(obj, self.__class__):
            return NotImplemented
        return self._parts == obj._parts
    
    def __len__(self) -> int:
        return len(self._parts)
    
    @overload
    def __getitem__(self, index: int) -> str: ...
    
    @overload
    def __getitem__(self, index: slice) -> list[str]: ...
    
    def __getitem__(self, index: int | slice) -> str | list[str]:
        return self._parts[index]


class _NprNameErrs(enum.IntEnum):
    NO_DATE = 1
    """8-digit date not found"""
    INVALID_DATE = 2
    """8-digit date is not valid"""
    UNSLUGIFIED_POD_NAME = 3
    """The podcast name is not slugified well."""
    OBSCURE_POD_NAME = 4
    """The podcast name is not clear."""


_quitReq = False
"""Specifies whether user requested to terminate the process immaturely."""

_AUDIO_EXTS: Iterable[str] = ['.mp3', '.m4a',]


_SLUG_REGEX = r'([a-z0-9]+{delimiter}*)+'

_NPR_NAME_REGEX = r"""
    ^
    (?P<podName>.*?)
    (?P<date>\d{8})
    (?P<description>.*)
    $
"""
_NPR_NAME_PATT = re.compile(_NPR_NAME_REGEX, re.VERBOSE)


@lru_cache(maxsize=128) 
def _getSlugPatt(delimiter: str) -> re.Pattern[str]:
    """Gets the `re` pattern for the specified delimiter. This API offload
    the client code of managing and caching the patters.
    """
    escDelim = re.escape(delimiter)
    regex = _SLUG_REGEX.format(delimiter=escDelim)
    return re.compile(regex)


def _nameToParts(name: str) -> _NprNameParts | None:
    """Parses the slugified name into its parts and returns the parts if
    the name is valid otherwise returns `None`. If the parse process is
    successful, it also finds the position of the date field in the parts
    of the name.
    """
    parts = None
    match_ = _getSlugPatt('_').fullmatch(name)
    if match_:
        parts = _NprNameParts()
        parts._parts = list(filter(None, name.split('_')))
    else:
        match_ = _getSlugPatt('-').fullmatch(name)
        if match_:
            parts = _NprNameParts()
            parts._parts = list(filter(None, name.split('-')))
    if parts is None:
        return None
    # Finding date...
    for i, part in enumerate(parts._parts):
        if len(part) == 8 and part.isdigit():
            parts._dateIdx = i
            break
    return parts


def _is8Date(date: str) -> bool:
    """Checks if the date string is in the format of YYYYMMDD."""
    try:
        datetime.strptime(date, "%Y%m%d")
    except ValueError:
        return False
    return True


def _normalizeNprFileName(name: str) -> str | _NprNameErrs:
    parts = _nameToParts(name)
    if parts is None:
        return _NprNameErrs.UNSLUGIFIED_POD_NAME
    # Checking date field existence...
    if parts.dateIdx is None:
        return _NprNameErrs.NO_DATE
    # Checking date validity...
    if not _is8Date(parts[parts.dateIdx]):
        return _NprNameErrs.INVALID_DATE
    # Reconstructing name...
    if parts.dateIdx == 0:
        return _NprNameErrs.OBSCURE_POD_NAME
    podName = '_'.join(parts[:parts.dateIdx])
    description = '_'.join(parts[parts.dateIdx + 1:])
    return f'{podName}___{parts[parts.dateIdx]}_{description}'


def _checkPodFiles(dir_: Path) -> Generator[None, Path | None, None]:
    print(_STRS.NPR_POD_DIR.format(dir_=dir_))
    file: Path | None = yield
    while file is not None:
        stem = file.stem
        newStem = _normalizeNprFileName(stem)
        if isinstance(newStem, _NprNameErrs):
            print(_STRS.BAD_NPR_NAME.format(stem=stem, reason=newStem.name))
        elif stem == newStem:
            print(_STRS.NAME_OK.format(stem=stem))
        else:
            # Renaing the file...
            #file.rename(file.with_stem(newStem))
            print(_STRS.RENAMED.format(old_stem=stem, new_stem=newStem))
        #
        file = yield


def _iterDir(dir_: Path) -> None:
    """Iterates over the provided folder and all its sub-folders for audio
    files. It riases `NotADirectoryError` if the provided path is not a
    valid directory. By setting the global `_quitReq` to `True`, it stops
    and returns as soon as possible.
    """
    # Declaring stuff ---------------------------
    global _quitReq
    subdirs = list[Path]()
    item: Path
    # Iterating over the current folder ---------
    if not dir_.is_dir():
        raise NotADirectoryError(
            f"The provided path {dir_} is not a directory.")
    podFilesChecker = _checkPodFiles(dir_)
    next(podFilesChecker)
    for item in dir_.iterdir():
        if _quitReq:
            return
        try:
            item.resolve(strict=True)
        except OSError:
            continue
        if item.is_dir():
            subdirs.append(item)
        elif item.is_file():
            if item.suffix.lower() in _AUDIO_EXTS:
                podFilesChecker.send(item)
        else:
            sys.stderr.write(_STRS.UNKNOWN_FS_ITEM.format(item=item) + '\n')
    # Finishing process of files in the current folder...
    try:
        podFilesChecker.send(None)
    except StopIteration:
        pass
    del podFilesChecker
    # Iterating over sub-folders ----------------
    for item in subdirs:
        if _quitReq:
            return
        _iterDir(item)


def main() -> None:
    # Printing the app info...
    print('=' * 60)
    print('\t', _STRS.APP_NAME)
    print('\t', _STRS.APP_DESCR)
    print('=' * 60)
    # Getting NPR podcasts dir...
    while True:
        # Getting a folder...
        try:
            dir_ = input(_STRS.ENTER_NPR_DIR)
        except KeyboardInterrupt:
            break
        # Iterating the folder...
        try:
            _iterDir(Path(dir_))
            break
        except NotADirectoryError as err:
            print(_STRS.BAD_DIR.format(reason=str(err)))


def _requestQuit(sig: int, frame: FrameType | None) -> None:
    global _quitReq
    _quitReq = True


if __name__ == '__main__':
    signal.signal(signal.SIGINT, _requestQuit)
    main()
