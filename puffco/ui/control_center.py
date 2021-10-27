from asyncio import ensure_future

from PyQt5.QtWidgets import QFrame, QLabel
from PyQt5.QtGui import QFont, QColor, QIcon
from .elements import ImageButton

button_font = QFont()
button_font.setPointSize(12)
button_font.setStretch(QFont.Unstretched * 1.5)


class ControlButton(ImageButton):
    ENABLED = False
    PATH = ':/assets/controlcenter_button.png'

    def __init__(self, parent, btn_text, asset_fp, size, setting, **kwargs):
        self._callback = kwargs.get('callback', None)
        super(ControlButton, self).__init__(self.PATH, parent, **kwargs)
        self._text = QLabel(btn_text, self)
        self._text.setFont(button_font)
        self._text.move(115, 45)
        self._text.update()
        self.btn_icon = ImageButton(asset_fp, self, size=size)
        self.btn_icon.move(65, 50)
        self.clicked.connect(self.on_click)
        self.setting_name = setting

    def on_click(self):
        self.ENABLED = not self.ENABLED
        settings.setValue(self.setting_name, self.ENABLED)

        color = QColor(255, 255, 255)
        if self.ENABLED:
            color = QColor(0, 0, 0)
            self._text.setStyleSheet('color: black;')
            pixmap = self.alter_pixmap(self.PATH, self.iconSize(), True, color=None)

        else:
            self._text.setStyleSheet('color: white;')
            pixmap = self.alter_pixmap(self.PATH, self.iconSize(), False, color=None)

        self.setIcon(QIcon(pixmap))
        pixmap = self.btn_icon.alter_pixmap(self.btn_icon.path, self.btn_icon.iconSize(), True, color)
        self.btn_icon.setIcon(QIcon(pixmap))

        if self._callback:
            self._callback(self.ENABLED)


class ControlCenter(QFrame):
    CONTROLS = []

    def __init__(self, parent):
        super(ControlCenter, self).__init__(parent)
        self.setHidden(True)
        self.setFixedSize(parent.size())
        self.setStyleSheet('background: rgba(105, 105, 105, 0.95);')
        self.title = QLabel('CONTROL CENTER', self)
        self.title.setStyleSheet('background: transparent;')
        self.title.move((parent.width() / 2) - (self.title.width() / 2), 20)

        self.a = ImageButton(':/assets/icon_rocket.png', self, paint=False, size=(54, 54))
        self.a.move((parent.width() / 2), 150)

        self.power_button = ImageButton(':/assets/icon_light_powermode.png', self, paint=False, size=(54, 54))
        self.power_button.move((parent.width()/2) + 70, 150)

        self.lantern_mode = ControlButton(self, 'LANTERN\nMODE', ':/assets/icon_lanternmode.png', (26, 42),
                                          'Modes/Lantern', paint=False)
        self.lantern_mode.move(self.a.x() - 57, self.power_button.y() + 45)
        self.lantern_mode.btn_icon.move(65, 45)

        self.ready_mode = ControlButton(self, 'READY\nMODE', ':/assets/icon_readymode.png', (26, 36),
                                        'Modes/Ready', paint=False)  # callback not needed here
        self.ready_mode.move(self.a.x() - 57, self.lantern_mode.y() + 100)

        self.stealth_mode = ControlButton(self, 'STEALTH\nMODE', ':/assets/icon_stealthmode.png', (42, 30),
                                          'Modes/Stealth', paint=False, callback=self.toggle_stealth)
        self.stealth_mode.move(self.a.x() - 57, self.ready_mode.y() + 100)
        self.stealth_mode.btn_icon.move(55, 50)

        self.CONTROLS = [self.lantern_mode, self.ready_mode, self.stealth_mode]

    @staticmethod
    def toggle_stealth(enabled):
        ensure_future(client.set_stealth_mode(enabled)).done()
