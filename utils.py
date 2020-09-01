from kivy.utils import platform

def is_mobile():
    return platform in ['ios', 'android']