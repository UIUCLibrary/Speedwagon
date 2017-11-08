import typing
import zipfile
import urllib.request
import hashlib
import platform

import shutil
from collections import namedtuple
import os
import enum
import sys
import argparse

Runtime = namedtuple("Runtime", ("url", "md5"))
RUNTIME_CACHE = "build/runtimes/"


class ARCHITECTURES(enum.Enum):
    x86 = "win32"
    x64 = "amd64"


RUNTIMES = {
    ("3.6.3", ARCHITECTURES.x64): Runtime("https://www.python.org/ftp/python/3.6.3/python-3.6.3-embed-amd64.zip",
                                          "b1daa2a41589d7504117991104b96fe5"),
    ("3.6.3", ARCHITECTURES.x86): Runtime("https://www.python.org/ftp/python/3.6.3/python-3.6.3-embed-win32.zip",
                                          "cf1c75ad7ccf9dec57ba7269198fd56b"),
    ("3.6.2", ARCHITECTURES.x64): Runtime("https://www.python.org/ftp/python/3.6.2/python-3.6.2-embed-amd64.zip",
                                          "0fdfe9f79e0991815d6fc1712871c17f"),
    ("3.6.2", ARCHITECTURES.x86): Runtime("https://www.python.org/ftp/python/3.6.2/python-3.6.2-embed-win32.zip",
                                          "2ca4768fdbadf6e670e97857bfab83e8"),
    ("3.6.1", ARCHITECTURES.x64): Runtime("https://www.python.org/ftp/python/3.6.1/python-3.6.1-amd64.exe",
                                          "ad69fdacde90f2ce8286c279b11ca188")
}


def valid_file(file, expected_md5):
    hash_md5 = hashlib.md5()
    with open(file, "rb") as f:
        for chunk in iter(lambda: f.read(2 ** 20), b""):
            hash_md5.update(chunk)
    if hash_md5.hexdigest() != expected_md5:
        raise IOError("{} doesn't match expected hash.")


def download_runtime(url, md5, destination):
    filename = os.path.basename(url)
    try:
        tmp_file, headers = urllib.request.urlretrieve(url)
        valid_file(tmp_file, md5)
        final_path = os.path.join(destination, filename)
        shutil.move(tmp_file, final_path)
        return os.path.abspath(final_path)

    finally:
        urllib.request.urlcleanup()


def get_download_info(version: str, arch: typing.Union[str, ARCHITECTURES]):
    if isinstance(arch, enum.Enum):
        arch_bit = arch.value
    elif isinstance(arch, str):
        arch_bit = ARCHITECTURES[arch]
    else:
        raise TypeError("Invalid type for arch")
    return RUNTIMES[(version, arch_bit)]


def get_arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("destination", help="Destination to install the python runtime")
    parser.add_argument("--version", default="{}.{}.{}".format(sys.version_info.major, sys.version_info.minor,
                                                               sys.version_info.micro))
    parser.add_argument("--arch", default="x64" if platform.architecture()[0] == "64bit" else "x86")
    return parser


def list_types():
    print("\n{:<10}Arch".format("Version"))
    print("-" * 15)
    print()
    for version, arch in RUNTIMES:
        print("{:<10}{}".format(version, arch.name))


def install_python(filename, destination):
    with zipfile.ZipFile(filename, "r") as zip_ref:
        zip_ref.extractall(destination)


def find_path_file(path):
    path_files = []
    for file in filter(lambda i: i.is_file(), os.scandir(path)):
        if os.path.splitext(file.name)[1] == "._pth":
            path_files.append(file.path)

    if len(path_files) == 0:
        raise FileNotFoundError
    elif len(path_files) > 1:
        raise RuntimeError("Multiple files with extension ._pth found, [{}]".format(", ".join(path_files)))
    else:
        return path_files[0]


def fixup_python_runtime(path):
    path_file = find_path_file(path)
    print("Adding line \"./lib\" to {}".format(path_file))
    with open(path_file, "a") as fw:
        fw.write("\n./lib\n")
        fw.write("\n./lib/site-packages\n")


def main():
    if len(sys.argv) > 1:
        if "--list" in sys.argv:
            print("\nKnown versions:")
            list_types()
            sys.exit()

    arg_parser = get_arg_parser()
    args = arg_parser.parse_args()
    try:
        runtime = get_download_info(version=args.version, arch=args.arch)
    except KeyError as e:
        print("Invalid version: {} {}".format(args.version, args.arch), file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(RUNTIME_CACHE):
        print("Creating {}".format(RUNTIME_CACHE))
        os.makedirs(RUNTIME_CACHE)
    cached_file = os.path.join(RUNTIME_CACHE, os.path.basename(runtime.url))
    if os.path.exists(cached_file):
        print("Using cached {}".format(cached_file))
        file_name = cached_file
    else:
        print("Downloading runtime.")
        file_name = download_runtime(url=runtime.url, md5=runtime.md5, destination=RUNTIME_CACHE)
        print("Downloaded {}".format(os.path.basename(file_name)))
        print("Adding Python runtime to {}".format(args.destination))
    install_python(file_name, destination=args.destination)
    fixup_python_runtime(path=args.destination)


if __name__ == '__main__':
    main()
