from pythonforandroid.recipe import PythonRecipe
from pythonforandroid.logger import (logger, info, warning, debug, shprint, info_main)
from pythonforandroid.util import current_directory

from os.path import join
import glob
import sh

#
# Minimize the size of the apk by removing unneeded stuff
#
class Minimize(PythonRecipe):
    version = '0.1'
    name = 'Minimize'
    depends = ['kivy'] # do this last
    def __init__(self):
        super().__init__()

    def should_build(self, arch):
        return True
    
    def build_arch(self, arch=None):
        junk = ['sqlite', 'ssl', 'ffi', 'crypto' ]
        libs_dir = self.ctx.get_libs_dir(arch.arch)
        print (sh.ls('-l','{}'.format(libs_dir)))
        extra_libs = [sh.glob(join('{}', '*' + j + '*').format(libs_dir)) for j in junk]
        if not extra_libs:
            info('No junk found.')
        else:
            for libs in extra_libs:
                for lso in libs:
                    warning (lso)

        python_install_dirs = glob.glob(join(self.ctx.python_installs_dir, '*'))
        for python_install in python_install_dirs:
            debug (sh.ls('-l','{}'.format(python_install)))
            exe_files =  sh.glob(join('{}', 'setuptools', '*.exe').format(python_install))
            for f in exe_files:
                print (sh.rm(f))

recipe = Minimize() 
