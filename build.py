from buildozer import Buildozer
import sys
import sh


class Builder(Buildozer):
    def __init__(self):
        super().__init__()
        try:
            print(sh.cp(
                'p4a-recipes/FastSDL/__init__.py',
                '.buildozer/android/platform/python-for-android/pythonforandroid/recipes/sdl2/'
            ))
        except:
            pass

    def set_target(self, target):
        super().set_target(target)
        if getattr(self.target, '_p4a', None):
            self.__p4a = self.target._p4a
            self.target._p4a = self.p4a

    def p4a(self, cmd, **kwargs):
        cmd += ' --blacklist-requirements=sqlite3,openssl,libffi'
        return self.__p4a(cmd, **kwargs) 

    def cmd(self, command, **kwargs):
        print()
        print(command, kwargs)
        print()
        return super().cmd(command, **kwargs)

if __name__=='__main__':
    #Builder().run_command(sys.argv[1:])
    Builder().run_command(['android', 'debug', 'deploy'])

