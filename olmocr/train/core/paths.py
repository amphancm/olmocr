import glob
import os
import re
from concurrent.futures import ThreadPoolExecutor
from functools import partial, reduce
from hashlib import sha256
from itertools import chain
from pathlib import Path
from shutil import copyfileobj
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple, Union
from urllib.parse import urlparse

import platformdirs
import smart_open
from fsspec import AbstractFileSystem, get_filesystem_class
from smart_open.compression import get_supported_extensions

from .loggers import LOGGER_PREFIX, get_logger

__all__ = [
    "glob_path",
    "sub_prefix",
    "add_suffix",
    "sub_suffix",
    "make_relative",
    "mkdir_p",
    "split_path",
    "join_path",
    "is_glob",
    "split_glob",
    "partition_path",
]


FS_KWARGS: Dict[str, Dict[str, Any]] = {
    "": {"auto_mkdir": True},
}


RE_ANY_ESCAPE = re.compile(r"(?<!\\)(\*\?\[\])")
RE_GLOB_STAR_ESCAPE = re.compile(r"(?<!\\)\*")
RE_GLOB_ONE_ESCAPE = re.compile(r"(?<!\\)\?")
RE_GLOB_OPEN_ESCAPE = re.compile(r"(?<!\\)\[")
RE_GLOB_CLOSE_ESCAPE = re.compile(r"(?<!\\)\]")
ESCAPE_SYMBOLS_MAP = {"*": "\u2581", "?": "\u2582", "[": "\u2583", "]": "\u2584"}
REVERSE_ESCAPE_SYMBOLS_MAP = {v: k for k, v in ESCAPE_SYMBOLS_MAP.items()}
PATCHED_GLOB = False


LOGGER = get_logger(__name__)


def get_fs(path: Union[Path, str]) -> AbstractFileSystem:
    """
    Get the filesystem class for a given path.
    """
    path = str(path)
    protocol = urlparse(path).scheme
    fs = get_filesystem_class(protocol)(**FS_KWARGS.get(protocol, {}))

    global PATCHED_GLOB  # pylint: disable=global-statement

    # patch glob method to support recursive globbing
    if protocol == "" and not PATCHED_GLOB:
        fs.glob = partial(glob.glob, recursive=True)

        # only patch once
        PATCHED_GLOB = True

    return fs


def _escape_glob(s: Union[str, Path]) -> str:
    """
    Escape glob characters in a string.
    """
    s = str(s)
    s = RE_GLOB_STAR_ESCAPE.sub(ESCAPE_SYMBOLS_MAP["*"], s)
    s = RE_GLOB_ONE_ESCAPE.sub(ESCAPE_SYMBOLS_MAP["?"], s)
    s = RE_GLOB_OPEN_ESCAPE.sub(ESCAPE_SYMBOLS_MAP["["], s)
    s = RE_GLOB_CLOSE_ESCAPE.sub(ESCAPE_SYMBOLS_MAP["]"], s)
    return s


def _unescape_glob(s: Union[str, Path]) -> str:
    """
    Unescape glob characters in a string.
    """
    s = str(s)
    for k, v in REVERSE_ESCAPE_SYMBOLS_MAP.items():
        s = s.replace(k, v)
    return s


def _pathify(path: Union[Path, str]) -> Tuple[str, Path]:
    """
    Return the protocol and path of a given path.
    """
    path = _escape_glob(str(path))
    parsed = urlparse(path)
    path = Path(f"{parsed.netloc}/{parsed.path}") if parsed.netloc else Path(parsed.path)
    return parsed.scheme, path


def _unpathify(protocol: str, path: Path) -> str:
    """
    Return a path from its protocol and path components.
    """
    path_str = _unescape_glob(str(path))
    if protocol:
        path_str = f"{protocol}://{path_str.lstrip('/')}"
    return path_str


def remove_params(path: str) -> str:
    """
    Remove parameters from a path.
    """
    parsed = urlparse(path)
    return (f"{parsed.scheme}://" if parsed.scheme else "") + f"{parsed.netloc}{parsed.path}"


def is_local(path: str) -> bool:
    """
    Check if a path is local.
    """
    prot, _ = _pathify(path)
    return prot == "" or prot == "file"


def copy_file(src: str, dest: str) -> None:
    """Copy a file using shutil.copyfileobj for efficient chunked copying."""
    # Ensure the destination directory exists
    os.makedirs(os.path.dirname(dest), exist_ok=True)

    with smart_open.open(src, "rb") as src_file, smart_open.open(dest, "wb") as dest_file:
        copyfileobj(src_file, dest_file)        


def copy_dir(src: str, dst: str, src_fs: Optional[AbstractFileSystem] = None, dst_fs: Optional[AbstractFileSystem] = None):
    """Copy a directory using a ThreadPoolExecutor for parallel file copying."""
    src_fs = src_fs or get_fs(src)
    dst_fs = dst_fs or get_fs(dst)
    logger = get_logger(__name__)

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = []

        for src_path in glob_path(src, yield_dirs=True, fs=src_fs):
            rel_path = sub_prefix(src_path, src)
            dest_path = join_path("", dst, rel_path)

            if is_dir(src_path, fs=src_fs):
                # Recursively copy directories
                copy_dir(src=src_path, dst=dest_path, src_fs=src_fs, dst_fs=dst_fs)
            else:
                # File; copy over using the executor for parallelism
                logger.info(f"Copying {src_path} to {dest_path}")
                futures.append(executor.submit(copy_file, src_path, dest_path))

        # Wait for all futures to complete
        for future in futures:
            future.result()  # This will raise an exception if any of the threads failed


def delete_file(path: str, ignore_missing: bool = False, fs: Optional[AbstractFileSystem] = None) -> bool:
    """Delete a file."""

    fs = fs or get_fs(path)
    try:
        fs.rm(path)
        deleted = True
    except FileNotFoundError as ex:
        if not ignore_missing:
            raise ex
        deleted = False

    return deleted


def get_size(path: str, fs: Optional[AbstractFileSystem] = None) -> int:
    """Get the size of a file"""

    fs = fs or get_fs(path)

    if not exists(path, fs=fs):
        raise ValueError(f"Path {path} does not exist")
    if is_dir(path, fs=fs):
        raise ValueError(f"Path {path} is a directory")

    return fs.info(path)["size"]


def delete_dir(path: str, ignore_missing: bool = False, fs: Optional[AbstractFileSystem] = None) -> bool:
    """Delete a directory."""

    fs = fs or get_fs(path)
    try:
        fs.rm(path, recursive=True)
        deleted = True
    except FileNotFoundError as ex:
        if not ignore_missing:
            raise ex
        deleted = False

    return deleted


def partition_path(path: str) -> Tuple[str, Tuple[str, ...], Tuple[str, ...]]:
    """Partition a path into its protocol, symbols before a glob, and symbols after a glob."""
    # split the path into its protocol and path components
    prot, path_obj = _pathify(path)

    # we need to first figure out if this path has a glob by checking if any of the escaped symbols for
    # globs are in the path.
    glob_locs = [i for i, p in enumerate(path_obj.parts) if any(c in p for c in REVERSE_ESCAPE_SYMBOLS_MAP)]

    # make the path components before the glob
    pre_glob_path = path_obj.parts[: glob_locs[0]] if glob_locs else path_obj.parts
    pre_glob_path = tuple(_unescape_glob(p) for p in pre_glob_path)

    # make the path components after the glob
    post_glob_path = path_obj.parts[glob_locs[0] + 1 :] if glob_locs else ()
    post_glob_path = tuple(_unescape_glob(p) for p in post_glob_path)

    return prot, pre_glob_path, post_glob_path


def split_path(path: str) -> Tuple[str, Tuple[str, ...]]:
    """
    Split a path into its protocol and path components.
    """
    protocol, _path = _pathify(path)
    return protocol, tuple(_unescape_glob(p) for p in _path.parts)


def join_path(protocol: Union[str, None], *parts: Union[str, Iterable[str]]) -> str:
    """
    Join a path from its protocol and path components.
    """
    all_prots, all_parts = zip(*(_pathify(p) for p in chain.from_iterable([p] if isinstance(p, str) else p for p in parts)))
    path = str(Path(*all_parts)).rstrip("/")
    protocol = protocol or str(all_prots[0])

    if protocol:
        path = f"{protocol}://{path.lstrip('/')}"
    return _unescape_glob(path)


def glob_path(
    path: Union[Path, str],
    hidden_files: bool = False,
    autoglob_dirs: bool = True,
    recursive_dirs: bool = False,
    yield_dirs: bool = True,
    fs: Optional[AbstractFileSystem] = None,
) -> Iterator[str]:
    """
    Expand a glob path into a list of paths.
    """
    protocol, parsed_path = _pathify(path)
    fs = fs or get_fs(path)

    if autoglob_dirs and fs.isdir(path):
        path = join_path(protocol, _unescape_glob(parsed_path), "*")

    if "*" not in str(path):
        # nothing to glob
        yield str(path)
        return

    for gl in fs.glob(path):
        gl = str(gl)

        if not hidden_files and Path(gl).name.startswith("."):
            continue

        if fs.isdir(gl):
            if recursive_dirs:
                yield from glob_path(
                    gl,
                    hidden_files=hidden_files,
                    autoglob_dirs=autoglob_dirs,
                    recursive_dirs=recursive_dirs,
                    yield_dirs=yield_dirs,
                    fs=fs,
                )
            if yield_dirs:
                yield join_path(protocol, gl)
        else:
            yield join_path(protocol, gl)


def sub_prefix(a: str, b: str) -> str:
    """
    Return the relative path of b from a.
    """
    prot_a, path_a = _pathify(a)
    prot_b, path_b = _pathify(b)

    if prot_a != prot_b:
        raise ValueError(f"Protocols of {a} and {b} do not match")

    try:
        diff = str(path_a.relative_to(path_b))
    except ValueError:
        diff = join_path(prot_a, path_a.parts)

    return _unescape_glob(diff)


def sub_suffix(a: str, b: str) -> str:
    """
    Remove b from the end of a.
    """
    prot_a, path_a = _pathify(a)
    prot_b, path_b = _pathify(b)

    if prot_b:
        raise ValueError(f"{b} is not a relative path")

    sub_path = re.sub(f"{path_b}$", "", str(path_a))
    sub_prot = f"{prot_a}://" if prot_a else ""

    # need to trim '/' from the end if (a) '/' is not the only symbol in the path or
    # (b) there is a protocol so absolute paths don't make sense
    if sub_path != "/" or sub_prot:
        sub_path = sub_path.rstrip("/")

    return _unescape_glob(sub_prot + sub_path)


def add_suffix(a: str, b: str) -> str:
    """
    Return the the path of a joined with b.
    """
    prot_a, path_a = _pathify(a)
    prot_b, path_b = _pathify(b)

    if prot_b:
        raise ValueError(f"{b} is not a relative path")

    return join_path(prot_a, str(path_a / path_b))


def exists(path: str, fs: Optional[AbstractFileSystem] = None) -> bool:
    """Check if a path exists."""

    fs = fs or get_fs(path)
    return fs.exists(path)


def is_dir(path: str, fs: Optional[AbstractFileSystem] = None) -> bool:
    """Check if a path is a directory."""
    fs = fs or get_fs(path)
    if exists(path, fs=fs):
        return fs.isdir(path)
    return False


def is_file(path: str, fs: Optional[AbstractFileSystem] = None) -> bool:
    """Check if a path is a file."""
    fs = fs or get_fs(path)
    if exists(path, fs=fs):
        return fs.isfile(path)
    return False


def parent(path: str) -> str:
    """Get the parent directory of a path; if the parent is the root, return the root."""

    prot, parts = split_path(path)
    if len(parts) == 1:
        return path
    return join_path(prot, *parts[:-1])


def mkdir_p(path: str, fs: Optional[AbstractFileSystem] = None) -> None:
    """
    Create a directory if it does not exist.
    """
    if is_glob(path):
        raise ValueError(f"Cannot create directory with glob pattern: {path}")

    fs = fs or get_fs(path)
    fs.makedirs(path, exist_ok=True)


def make_relative(paths: List[str]) -> Tuple[str, List[str]]:
    """Find minimum longest root shared among all paths"""
    if len(paths) == 0:
        raise ValueError("Cannot make relative path of empty list")

    common_prot, common_parts, _ = partition_path(paths[0])

    for path in paths:
        current_prot, current_parts, _ = partition_path(path)
        if current_prot != common_prot:
            raise ValueError(f"Protocols of {path} and {paths[0]} do not match")

        for i in range(min(len(common_parts), len(current_parts))):
            if common_parts[i] != current_parts[i]:
                common_parts = common_parts[:i]
                break

    if len(common_parts) > 0:
        common_path = (f"{common_prot}://" if common_prot else "") + str(Path(*common_parts))
        relative_paths = [sub_prefix(path, common_path) for path in paths]
    else:
        common_path = f"{common_prot}://" if common_prot else ""
        relative_paths = [_unpathify("", _pathify(path)[1]) for path in paths]

    return common_path, relative_paths


def is_glob(path: str) -> bool:
    """
    Check if a path contains a glob wildcard.
    """
    return bool(re.search(r"(?<!\\)[*?[\]]", path))


def split_glob(path: str) -> Tuple[str, str]:
    """
    Partition a path on the first wildcard.
    """
    if not is_glob(path):
        # it's not a glob, so it's all path
        return path, ""

    if path[0] == "*":
        # starts with a glob, so it's all glob
        return "", path

    protocol, parts = split_path(path)

    i = min(i for i, c in enumerate(parts) if is_glob(c))

    if i == 0:
        # no path, so it's all glob
        return protocol, join_path("", *parts)

    path = join_path(protocol, *parts[:i])
    rest = join_path("", *parts[i:])
    return path, rest


def get_cache_dir() -> str:
    """
    Returns the path to the cache directory for the Dolma toolkit.
    If the directory does not exist, it will be created.

    Returns:
        str: The path to the cache directory.
    """
    loc = platformdirs.user_cache_dir(LOGGER_PREFIX)
    mkdir_p(loc)
    return loc


def resource_to_filename(resource: Union[str, bytes]) -> str:
    """
    Convert a ``resource`` into a hashed filename in a repeatable way. Preserves the file extensions.
    """
    _, (*_, orig_filename) = split_path(remove_params(str(resource)))
    _, extensions = split_basename_and_extension(orig_filename)

    resource_bytes = str(resource).encode("utf-8")
    resource_hash = sha256(resource_bytes)
    hash_filename = resource_hash.hexdigest() + extensions

    return hash_filename


def cached_path(path: str, fs: Optional[AbstractFileSystem] = None) -> str:
    """
    Returns the cached path for a given resource.

    If the resource is already available locally, the function returns the path as is.
    Otherwise, it downloads the resource from the specified path and saves it in the cache directory.

    Args:
        path (str): The path to the resource.

    Returns:
        str: The cached path of the resource.
    """
    if is_local(path):
        # Implementation goes here
        pass
        return path

    destination = f"{get_cache_dir()}/{resource_to_filename(path)}"

    remote_fs = fs or get_fs(path)
    local_fs = get_fs(destination)

    if exists(destination, fs=local_fs):
        LOGGER.info(f"Using cached file {destination} for {path}")
        return destination

    if is_dir(path, fs=remote_fs):
        for sub_path in glob_path(path, fs=remote_fs):
            rel_path = sub_prefix(sub_path, path)
            dest_path = join_path("", destination, rel_path)
            mkdir_p(parent(dest_path), fs=local_fs)
            LOGGER.info(f"Downloading {sub_path} to {dest_path}")
            with smart_open.open(sub_path, "rb") as src, smart_open.open(dest_path, "wb") as dest:
                dest.write(src.read())
    else:
        LOGGER.info(f"Downloading {path} to {destination}")
        with smart_open.open(path, "rb") as src, smart_open.open(destination, "wb") as dest:
            dest.write(src.read())

    return destination


def split_basename_and_extension(path: str) -> Tuple[str, str]:
    """
    Get the path and extension from a given file path. If a file has multiple
    extensions, they will be joined with a period, e.g. "foo/bar/baz.tar.gz"
    will return ("foo/bar/baz", ".tar.gz"). If the file has no extension, the
    second element of the tuple will be an empty string. Works with both local
    and remote (e.g. s3://) paths.

    Args:
        path (str): The file path.

    Returns:
        Tuple[str, str]: A tuple containing the path and extension.
    """
    prot, (*parts, filename) = split_path(path)
    base, *ext_parts = filename.split(".")
    ext = ("." + ".".join(ext_parts)) if ext_parts else ""
    return join_path(prot, *parts, base), ext


def decompress_path(path: str, dest: Optional[str] = None) -> str:
    """
    Decompresses a file at the given path and returns the path to the decompressed file.

    Args:
        path (str): The path to the file to be decompressed.
        dest (str, optional): The destination path for the decompressed file.
            If not provided, a destination path will be computed based on the original
            file name and the cache directory.

    Returns:
        str: The path to the decompressed file. If the file cannot be decompressed,
            the original path will be returned.
    """
    for supported_ext in get_supported_extensions():
        # not the supported extension
        if not path.endswith(supported_ext):
            continue

        if dest is None:
            # compute the name for the decompressed file; to do this, we first hash for
            # resource and then remove the extension.
            base_fn, ext = split_basename_and_extension(resource_to_filename(path))

            # to get the decompressed file name, we remove the bit of the extension that
            # indicates the compression type.
            decompressed_fn = base_fn + ext.replace(supported_ext, "")

            # finally, we get cache directory and join the decompressed file name to it
            dest = join_path("", get_cache_dir(), decompressed_fn)

        # here we do the actual decompression
        with smart_open.open(path, "rb") as fr, smart_open.open(dest, "wb") as fw:
            fw.write(fr.read())

        # return the path to the decompressed file
        return dest

    # already decompressed or can't be decompressed
    return path


def split_ext(path: str) -> Tuple[str, Tuple[str, ...], str]:
    """
    Split a path into its protocol and extensions.
    """
    prot, parts = split_path(path)
    if not parts:
        return prot, (), ""

    filename = parts[-1]
    extensions = []
    while True:
        filename, ext = os.path.splitext(filename)
        if not ext:
            break
        extensions.append(ext)

    return prot, (*parts[:-1], filename), "".join(reversed(extensions))


def get_unified_path(paths: List[str]) -> str:
    """Get a unified path for a list of paths."""

    if len(paths) == 1:
        # if there is only one path, we don't need to unify anything
        return paths[0]

    # get shared root for all paths; we will put the unified path here
    root, relative = make_relative(paths)

    # get the extension from the first path; assume all paths have the same extension
    _, _, ext = split_ext(relative[0])

    # hash all the sorted relative paths in order to get a unique name
    # the type: ignore is needed because mypy fails to infer the type of the lambda
    # (the "or" ensures that the lambda returns the same type as the first argument, which is a hash)
    h = reduce(lambda h, p: h.update(p.encode()) or h, sorted(relative), sha256())  # type: ignore

    # return the unified path
    return join_path(root, h.hexdigest() + ext)
