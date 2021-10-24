from PyQt5.QtWidgets import QFrame, QLabel
from PyQt5.QtGui import QFont
from .elements import ImageButton

button_font = QFont()
button_font.setPointSize(12)
button_font.setStretch(QFont.Unstretched * 1.5)


class ControlButton(ImageButton):
    def __init__(self, parent, btn_text, asset_fp, size, **kwargs):
        super(ControlButton, self).__init__(':/assets/controlcenter_button.png', parent, **kwargs)
        self._text = QLabel(btn_text, self)
        self._text.setFont(button_font)
        self._text.move(115, 45)
        self._text.update()
        self.btn_icon = ImageButton(asset_fp, self, size=size)
        self.btn_icon.move(65, 50)


class ControlCenter(QFrame):
    def __init__(self, parent):
        super(ControlCenter, self).__init__(parent)
        self.setFixedSize(parent.size())
        self.setStyleSheet('background: rgba(105, 105, 105, 0.95);')
        self.title = QLabel('CONTROL CENTER', self)
        self.title.setStyleSheet('background: transparent;')
        self.title.move((parent.width() / 2) - (self.title.width() / 2), 20)

        self.a = ImageButton(':/assets/icon_rocket.png', self, paint=False, size=(54, 54))
        self.a.move((parent.width() / 2), 150)

        self.power_button = ImageButton(':/assets/icon_light_powermode.png', self, paint=False, size=(54, 54))
        self.power_button.move((parent.width()/2) + 70, 150)

        self.lantern_mode = ControlButton(self, 'LANTERN\nMODE', ':/assets/icon_lanternmode.png', (26, 42), paint=False)
        self.lantern_mode.move(self.a.x() - 57, self.power_button.y() + 45)
        self.lantern_mode.btn_icon.move(65, 45)

        self.ready_mode = ControlButton(self, 'READY\nMODE', ':/assets/icon_readymode.png', (26, 36),
                                        paint=False)
        self.ready_mode.move(self.a.x() - 57, self.lantern_mode.y() + 100)

        self.stealth_mode = ControlButton(self, 'STEALTH\nMODE', ':/assets/icon_stealthmode.png', (42, 30), paint=False)
        self.stealth_mode.move(self.a.x() - 57, self.ready_mode.y() + 100)
        self.stealth_mode.btn_icon.move(55, 50)
