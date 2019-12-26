#
# Much of this copied from https://github.com/pybind/python_example.git
#

import sys

if sys.version_info[0] < 3:
    sys.stderr.write("ERROR: robotpy-cscore requires python 3!")
    exit(1)

import fnmatch
import glob
import os
from os.path import dirname, exists, join
from setuptools import find_packages, setup, Extension
from setuptools.command.build_ext import build_ext
import subprocess
import sys
import setuptools

setup_dir = dirname(__file__)
git_dir = join(setup_dir, ".git")
base_package = "cscore"
version_file = join(setup_dir, base_package, "version.py")

# Automatically generate a version.py based on the git version
if exists(git_dir):
    p = subprocess.Popen(
        ["git", "describe", "--tags", "--long", "--dirty=-dirty"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    out, err = p.communicate()
    # Make sure the git version has at least one tag
    if err:
        print("Error: You need to create a tag for this repo to use the builder")
        sys.exit(1)

    # Convert git version to PEP440 compliant version
    # - Older versions of pip choke on local identifiers, so we can't include the git commit
    v, commits, local = out.decode("utf-8").rstrip().split("-", 2)
    if commits != "0" or "-dirty" in local:
        v = "%s.post0.dev%s" % (v, commits)

    # Create the version.py file
    with open(version_file, "w") as fp:
        fp.write("# Autogenerated by setup.py\n__version__ = '{0}'".format(v))

if exists(version_file):
    with open(join(setup_dir, base_package, "version.py"), "r") as fp:
        exec(fp.read(), globals())
else:
    __version__ = "master"

with open(join(setup_dir, "README.rst"), "r") as readme_file:
    long_description = readme_file.read()


# try to use pkgconfig to find compile parameters for OpenCV
# Note: pkg-config is available for Windows, so try it on all platforms
# default: no additional directories needed
opencv_pkg = {"include_dirs": [""],
              "library_dirs": [""]}
try:
    import pkgconfig

    if pkgconfig.exists("opencv4"):
        opencv_pkg = pkgconfig.parse("opencv4")
    elif pkgconfig.exists("opencv"):
        opencv_pkg = pkgconfig.parse("opencv")
    else:
        sys.stderr.write("ERROR: unable to find suitable OpenCV library with pkg-config")
        sys.stderr.write("  If you compiled OpenCV, be sure to include CMake flag '-D OPENCV_GENERATE_PKGCONFIG=ON'")
        exit(3)
except ModuleNotFoundError:
    pass


#
# pybind-specific compilation stuff
#


class get_numpy_include(object):
    def __str__(self):
        import numpy as np

        return np.get_include()


def get_opencv_lib(name):
    lib = "opencv_" + name
    if sys.platform == "win32":
        import cv2

        lib += cv2.__version__.replace(".", "")
    return lib


# As of Python 3.6, CCompiler has a `has_flag` method.
# cf http://bugs.python.org/issue26689
def has_flag(compiler, flagname):
    """Return a boolean indicating whether a flag name is supported on
    the specified compiler.
    """
    import tempfile

    with tempfile.NamedTemporaryFile("w", suffix=".cpp") as f:
        f.write("int main (int argc, char **argv) { return 0; }")
        try:
            compiler.compile([f.name], extra_postargs=[flagname])
        except setuptools.distutils.errors.CompileError:
            return False
    return True


def cpp_flag(compiler):
    """Return the -std=c++[11/14/17] compiler flag.

    The highest version available is preferred.
    """
    if has_flag(compiler, "-std=c++17"):
        return "-std=c++17"
    else:
        raise RuntimeError("Unsupported compiler -- at least C++17 support is needed!")


class BuildExt(build_ext):
    """A custom build extension for adding compiler-specific options."""

    c_opts = {"msvc": ["/EHsc", "/DNOMINMAX"], "unix": []}

    if sys.platform == "darwin":
        c_opts["unix"] += ["-stdlib=libc++", "-mmacosx-version-min=10.7"]

    def build_extensions(self):
        ct = self.compiler.compiler_type
        opts = self.c_opts.get(ct, [])
        if ct == "unix":
            opts.append('-DVERSION_INFO="%s"' % self.distribution.get_version())
            # TODO: this feels like a hack
            if not os.environ.get("RPY_DEBUG"):
                opts.append("-s")  # strip
                opts.append("-g0")  # remove debug symbols
            else:
                opts.append("-O0")
            opts.append(cpp_flag(self.compiler))
            if has_flag(self.compiler, "-fvisibility=hidden"):
                opts.append("-fvisibility=hidden")
            if sys.platform != "darwin":
                opts.append("-D_GNU_SOURCE")
        elif ct == "msvc":
            opts.append('/DVERSION_INFO=\\"%s\\"' % self.distribution.get_version())
        for ext in self.extensions:
            ext.extra_compile_args = opts
        build_ext.build_extensions(self)


def recursive_glob(d):
    for root, _, filenames in os.walk(d):
        for fname in fnmatch.filter(filenames, "*.cpp"):
            yield join(root, fname)


def get_cscore_sources(d):
    l = list(glob.glob(d + "/cpp/*.cpp"))
    if sys.platform == "win32":
        l.extend(glob.glob(d + "/windows/*.cpp"))
    elif sys.platform == "darwin":
        l.extend(glob.glob(d + "/osx/*.cpp"))
    else:
        l.extend(glob.glob(d + "/linux/*.cpp"))
    print(l)
    return l


def get_wpiutil_sources(d):
    jnifiles = list(glob.glob(d + "/jni/*.cpp"))
    l = [f for f in recursive_glob(d) if f not in jnifiles]
    return l


def get_libuv_sources(d):
    l = list(glob.glob(d + "/*.cpp"))
    if sys.platform == "win32":
        l.extend(glob.glob(d + "/win/*.cpp"))
    else:
        l.extend(
            d + "/unix/" + f
            for f in [
                "async.cpp",
                "core.cpp",
                "dl.cpp",
                "fs.cpp",
                "getaddrinfo.cpp",
                "getnameinfo.cpp",
                "loop-watcher.cpp",
                "loop.cpp",
                "pipe.cpp",
                "poll.cpp",
                "process.cpp",
                "signal.cpp",
                "stream.cpp",
                "tcp.cpp",
                "thread.cpp",
                "tty.cpp",
                "udp.cpp",
            ]
        )
        if sys.platform == "darwin":
            l.extend(
                d + "/unix/" + f
                for f in [
                    "bsd-ifaddrs.cpp",
                    "darwin.cpp",
                    "darwin-proctitle.cpp",
                    "fsevents.cpp",
                    "kqueue.cpp",
                    "proctitle.cpp",
                ]
            )
        else:
            l.extend(
                d + "/unix/" + f
                for f in [
                    "linux-core.cpp",
                    "linux-inotify.cpp",
                    "linux-syscalls.cpp",
                    "procfs-exepath.cpp",
                    "proctitle.cpp",
                    "sysinfo-loadavg.cpp",
                    # "sysinfo-memory.cpp",
                ]
            )
    return l


ext_modules = [
    Extension(
        "_cscore",
        ["src/_cscore.cpp", "src/ndarray_converter.cpp"]
        + get_cscore_sources("cscore_src/cscore/src/main/native")
        + get_wpiutil_sources("cscore_src/wpiutil/src/main/native/cpp")
        + get_libuv_sources("cscore_src/wpiutil/src/main/native/libuv/src"),
        include_dirs=[
            "pybind11/include",
            "cscore_src/cscore/src/main/native/include",
            "cscore_src/cscore/src/main/native/cpp",
            "cscore_src/wpiutil/src/main/native/include",
            "cscore_src/wpiutil/src/main/native/libuv/src",
            "cscore_src/wpiutil/src/main/native/libuv/include",
            get_numpy_include(),
        ]
        + opencv_pkg["include_dirs"],
        library_dirs=opencv_pkg["library_dirs"],
        libraries=[
            get_opencv_lib(name) for name in ("core", "highgui", "imgproc", "imgcodecs")
        ],
        language="c++",
    )
]

setup(
    name="robotpy-cscore",
    version=__version__,
    author="Dustin Spicuzza",
    author_email="dustin@virtualroadside.com",
    url="https://github.com/robotpy/robotpy-cscore",
    description="RobotPy bindings for cscore image processing library",
    long_description=long_description,
    packages=find_packages(),
    ext_modules=ext_modules,
    install_requires=["numpy", "pynetworktables"],
    license="BSD",
    zip_safe=False,
    cmdclass={"build_ext": BuildExt},
    entry_points={"robotpylib": ["info = cscore._info:Info"]},
)
