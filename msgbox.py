from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.event import EventDispatcher


class MessageBox(EventDispatcher):
    __events__ = ('on_close',)

    def __init__(self, title, message, size=(400, 250), on_close=None, font_size=22):
        self.value = None
        self.open = open
        if on_close:
            self.bind(on_close=on_close)

        def popup_callback(instance):
            self.value = instance.text.strip()
            self.popup.dismiss()
            self.dispatch('on_close')

        box = GridLayout(cols=1, rows=2)
        box.add_widget(Label(text=message, font_size=font_size))
        options = ([ 'Yes', 'No' ] if message.endswith('?') else [ 'Ok' ])
        buttonbox = BoxLayout(size_hint=(1,.5))
        btns = []
        for b in options:
            btns.append(Button(text=b, font_size=20))
            btns[-1].bind(on_press=popup_callback)
            buttonbox.add_widget(btns[-1])
        box.add_widget(buttonbox)

        self.popup = Popup(title=title, title_size=18, content=box,
            pos_hint={'center_x': .5, 'center_y':.5},
            size=size, size_hint=(None, None), auto_dismiss=False)

        self.popup.open()


    def on_close(self, *_):
        pass

