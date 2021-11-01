from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QFont, QColor, QIcon, QPixmap, QCursor
from PyQt5.QtWidgets import QFrame, QLabel, QSlider

from . import ensure_future
from .elements import ImageButton
from .profile_window import ColorSlider

button_font = QFont()
button_font.setPointSize(12)
button_font.setStretch(QFont.Unstretched * 1.5)

WIDE_SLIDER_STYLE = """
.QSlider {
    min-width: 100px;
    max-width: 100px;
    background: transparent;
}

.QSlider::groove:vertical {
    border: 1px solid #262626;
    width: 150px;
    background: #393939;
}

.QSlider::handle:vertical {
    background: #ffffff;
    height: 10px;
    margin-left: -20px;
    margin-right: -20px;
    border-radius: 30px;
}

.QSlider::add-page:vertical {
    background: #ffffff;
    border-color: #bbb;
}
"""


class ColorWheel(ColorSlider):
    ASSET = 'color_wheel.png'
    last_selected = None

    def __init__(self, parent):
        super(ColorWheel, self).__init__(parent)
        self.setStyleSheet('background: transparent;')
        self.cursor_pixmap = QPixmap(':/assets/wheel_cursor.png').scaled(16, 16)
        self.setCursor(QCursor(self.cursor_pixmap))
        self.move(60, 160)

        pixmap = self.pixmap()
        w, h = pixmap.width(), pixmap.height()
        if w >= self.width() or h >= self.height():
            pixmap = pixmap.scaled(parent.width(), parent.height() / 2,
                                   Qt.KeepAspectRatio)

            w, h = pixmap.width(), pixmap.height()
            self.image = self.image.resize((w, h))
            self.setFixedSize(w, h)
            self.setPixmap(pixmap)

    def mouseReleaseEvent(self, ev) -> None:
        if ev.button() != Qt.LeftButton:
            return

        if self.selecting and ((self.selected is None) or self.selected == self.last_selected):
            self.mouseMoveEvent(ev)
            self.last_selected = self.selected

        self.selecting = False

    def enterEvent(self, a0: QEvent) -> None:
        self.setCursor(QCursor(self.cursor_pixmap))

    def leaveEvent(self, a0: QEvent) -> None:
        self.setCursor(QCursor())


class LanternSettings(QFrame):
    last_selection = None

    def __init__(self, parent):
        super(LanternSettings, self).__init__(parent)
        self.setHidden(True)
        self.setFixedSize(parent.size())
        self.setStyleSheet('background: rgba(105, 105, 105, 0.95);')

        self.wheel = ColorWheel(self)

        self.preview = QLabel('', self)
        self.preview.setFixedSize(36, 36)
        self.preview.move(self.wheel.x() - 10, self.wheel.y() - 20)
        self.preview.setStyleSheet(f'border: 2px solid black;'
                                   f'background-color: rgb{255, 255, 255};')

        self.cancel_button = ImageButton(':/icons/cancel.png', self, callback=lambda _:
                                         parent.edit_lantern_settings(bool(self.wheel.selected), done=True))
        self.cancel_button.resize(48, 48)
        self.cancel_button.move(10, 6)


class ControlButton(ImageButton):
    ENABLED = False
    PATH = ':/icons/control_center_btn.png'

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
        self.lantern_settings = LanternSettings(self)

        self.boost_controls = ImageButton(':/icons/boost_mode.png', self, paint=False, size=(54, 54))
        self.boost_controls.move((parent.width() / 2), 150)

        self.power_button = ImageButton(':/icons/power_mode.png', self, paint=False, size=(54, 54))
        self.power_button.move((parent.width() / 2) + 70, 150)

        self.lantern_mode = ControlButton(self, 'LANTERN\nMODE', ':/icons/lantern_mode.png', (26, 42),
                                          'Modes/Lantern', paint=False, callback=self.edit_lantern_settings)
        self.lantern_mode.move(self.boost_controls.x() - 57, self.power_button.y() + 45)
        self.lantern_mode.btn_icon.move(65, 45)

        self.ready_mode = ControlButton(self, 'READY\nMODE', ':/icons/ready_mode.png', (26, 36),
                                        'Modes/Ready', paint=False)  # callback not needed here
        self.ready_mode.move(self.boost_controls.x() - 57, self.lantern_mode.y() + 100)

        self.stealth_mode = ControlButton(self, 'STEALTH\nMODE', ':/icons/stealth_mode.png', (42, 30),
                                          'Modes/Stealth', paint=False, callback=self.toggle_stealth)
        self.stealth_mode.move(self.boost_controls.x() - 57, self.ready_mode.y() + 100)
        self.stealth_mode.btn_icon.move(55, 50)

        self.lantern_brightness = QSlider(Qt.Vertical, self)
        self.lantern_brightness.setStyleSheet(WIDE_SLIDER_STYLE)
        self.lantern_brightness.setRange(0, 255)
        self.lantern_brightness.setValue(0)
        self.lantern_brightness.setTickInterval(1)
        self.lantern_brightness.setPageStep(5)
        self.lantern_brightness.setSingleStep(1)
        self.lantern_brightness.setFixedHeight((parent.height() / 2) - 15)
        self.lantern_brightness.move(75, (parent.height() / 4) - 25)
        self.lantern_brightness.valueChanged.connect(self.update_lantern_brightness)

        self.CONTROLS = [self.lantern_mode, self.ready_mode, self.stealth_mode]

    def edit_lantern_settings(self, enabled, done=False):
        ensure_future(client.send_lantern_status(enabled)).done()
        if enabled and not done:
            self.lantern_settings.show()
            self.lantern_settings.raise_()
        else:
            self.lantern_settings.lower()
            self.lantern_settings.hide()

    @staticmethod
    def toggle_stealth(enabled):
        ensure_future(client.set_stealth_mode(enabled)).done()

    @staticmethod
    def update_lantern_brightness(val):
        ensure_future(client.send_lantern_brightness(val)).done()
