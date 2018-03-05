# aspects of this build system are based on https://github.com/PySide/pyside-setup
from __future__ import print_function

from distutils import log
from distutils.errors import DistutilsExecError, DistutilsOptionError, DistutilsSetupError
import fnmatch
from itertools import chain
import os,sys
import shutil
import struct
import subprocess

from . import popenasync

__all__ = ['CopyCode', 'CopyDirStructure', 'GetNCPUS', 'GetSetupSrcDir', 'InitInit', 'IsPython64Bit', 'OptionValue',
           'RGlob', 'RunProcess', 'WrappedMkdir', 'WrappedMakedirs']

thisScriptDir = os.path.dirname(os.path.realpath(__file__))

def CopyCode(srcRoot, dstRoot, symlink=False):
    for srcPyPath in RGlob(srcRoot, pat='*.py', exclude='__init__*'):
        dstPyPath = os.path.relpath(srcPyPath, srcRoot)
        dstPyPath = os.path.join(dstRoot, dstPyPath)
        if symlink:
            # clean up existing link
            try:
                os.remove(dstPyPath)
            except OSError:
                pass
            os.symlink(srcPyPath, dstPyPath)
        else:
            shutil.copy2(srcPyPath, dstPyPath)

def CopyDirStructure(srcRoot, dstRoot):
    for d in RGlob(srcRoot, '*', kind='d'):
        d = os.path.relpath(d, srcRoot)
        d = os.path.join(dstRoot, d)
        WrappedMkdir(d)

def GetNCPUS():
    try:
        import multiprocessing
        NCPUS = multiprocessing.cpu_count()
    except ImportError:
        NCPUS = 1

def GetSetupSrcDir():
    ''' Get the original directory in which setup.py was located, even if setup.py is run through pip.
    "Platform-independent", though linux and windows untested.

    :return: setupSrcDir as a string
    '''
    dirVars = ['PWD', 'CD']
    for dirVar in dirVars:
        if os.environ[dirVar]:
            return os.environ[dirVar]

    # if we got here something went wrong, so raise an error
    DistutilsExecError('While looking for the original setup.py directory, os.environ did not contain relevant variable: %s' % dirVars)

def _InitInitSingle(path, template=None):
    initPath = os.path.join(path, '__init__.py')
    if template is not None:
        templatePath = os.path.join(thisScriptDir, template)
        shutil.copy(templatePath, initPath)
    else:
        f = open(initPath, 'w')
        f.close()

def InitInit(path, recursive=False, template=None):
    if recursive:
        for rPath,dPaths,fPaths in os.walk(path):
            print(os.path.join(rPath, '__init__'))
            _InitInitSingle(rPath, template=template)
    else:
        print(os.path.join(path, '__init__'))
        _InitInitSingle(path, template=template)

def IsPython64Bit():
    return (struct.calcsize("P") == 8)

def OptionValue(name):
    for index, option in enumerate(sys.argv):
        if option == '--' + name:
            if index+1 >= len(sys.argv):
                raise DistutilsOptionError(
                    'The option %s requires a value' % option)
            value = sys.argv[index+1]
            sys.argv[index:index+2] = []
            return value
        if option.startswith('--' + name + '='):
            value = option[len(name)+3:]
            sys.argv[index:index+1] = []
            return value
    env_val = os.getenv(name.upper().replace('-', '_'))
    return env_val

def RGlob(root, pat, abs=True, exclude=None, kind='f'):
    # the tup slices affect which parts of the tups returns from os.walk are used
    if kind=='f':
        tupSlice = slice(2,3)
    elif kind=='d':
        tupSlice = slice(1,2)
    elif kind=='b':
        tupSlice = slice(1,3)

    matches = []
    if exclude is None:
        if abs:
            for tups in os.walk(root):
                for filename in fnmatch.filter(chain(*tups[tupSlice]), pat):
                    matches.append(os.path.join(tups[0], filename))
        else:
            for tups in os.walk(root):
                for filename in fnmatch.filter(chain(*tups[tupSlice]), pat):
                    matches.append(filename)
    else:
        if abs:
            for tups in os.walk(root):
                for filename in set(fnmatch.filter(chain(*tups[tupSlice]), pat)) - set(fnmatch.filter(chain(*tups[tupSlice]), exclude)):
                    matches.append(os.path.join(tups[0], filename))
        else:
            for tups in os.walk(root):
                for filename in set(fnmatch.filter(chain(*tups[tupSlice]), pat)) - set(fnmatch.filter(chain(*tups[tupSlice]), exclude)):
                    matches.append(filename)
    return matches

def RunProcess(args, cwd=None, initial_env=None):
    def _log(buffer, checkNewLine=False):
        endsWithNewLine = False
        if buffer.endswith('\n'):
            endsWithNewLine = True
        if checkNewLine and buffer.find('\n') == -1:
            return buffer
        lines = buffer.splitlines()
        buffer = ''
        if checkNewLine and not endsWithNewLine:
            buffer = lines[-1]
            lines = lines[:-1]
        for line in lines:
            log.info(line.rstrip('\r'))
        return buffer

    _log("Running process: {0}".format(" ".join([(" " in x and '"{0}"'.format(x) or x) for x in args])))

#     if sys.platform != "win32":
#         try:
#             spawn(args)
#             return 0
#         except DistutilsExecError:
#             return -1

    shell = False
    if sys.platform == "win32":
        shell = True

    if initial_env is None:
        initial_env = os.environ

    proc = popenasync.Popen(args,
        cwd = cwd,
        stdin = subprocess.PIPE,
        stdout = subprocess.PIPE,
        stderr = subprocess.STDOUT,
        universal_newlines = 1,
        shell = shell,
        env = initial_env)

    log_buffer = None;
    while proc.poll() is None:
        log_buffer = _log(proc.read_async(wait=0.1, e=0))
    if log_buffer:
        _log(log_buffer)

    proc.wait()
    return proc.returncode

def WrappedMkdir(d, mode=0o755):
    try:
        os.mkdir(d, mode)
    except OSError:
        pass
    
def WrappedMakedirs(d, mode=0o755):
    try:
        os.makedirs(d, mode)
    except OSError:
        pass
