from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QFont, QColor, QIcon, QPixmap, QCursor
from PyQt5.QtWidgets import QFrame, QLabel, QSlider, QPushButton
from PIL import Image, ImageOps

from puffco.bluetooth.constants import *
from .elements import ImageButton
from .profile_window import ColorSlider
from .constants import WIDE_SLIDER_STYLE

button_font = QFont()
button_font.setPointSize(12)
button_font.setStretch(QFont.Unstretched * 1.5)


class BoostSettings(QFrame):
    HELP = "Boost Mode gives you the choice to add time, temperature, or both to your dabbing session.\n\n" \
           "Activate Boost Mode by double-clicking your peak button while dabbing."

    def __init__(self, parent):
        super(BoostSettings, self).__init__(parent)
        self.setHidden(True)
        self.setFixedSize(parent.size())
        self.setStyleSheet('background: rgba(105, 105, 105, 0.95);')

        self.title = QLabel('BOOST MODE', self)
        self.title.setStyleSheet('background: transparent;')
        self.title.move((parent.width() / 2) - (self.title.width() / 2), 20)

        self.help = QLabel(self.HELP, self)
        self.help.setFixedWidth(self.width() * .75)
        help_font = QFont(self.font().family(), 12)
        help_font.setStretch(help_font.Unstretched * 1.33)
        self.help.setFont(help_font)
        self.help.setStyleSheet('background: transparent;')
        self.help.setWordWrap(True)
        self.help.move(45, 70)

        self.reset_button = QPushButton('Reset', self)
        self.reset_button.setStyleSheet('background: transparent;')
        self.reset_button.clicked.connect(self.reset)
        self.reset_button.move(15, 15)
        self.cancel_button = ImageButton(':/icons/cancel.png', self, callback=self.exit)
        self.cancel_button.resize(48, 48)
        self.cancel_button.move(self.width() - self.cancel_button.width() - 10, 6)

        self.temp_slider = QSlider(Qt.Vertical, self)
        self.temp_slider.setStyleSheet(WIDE_SLIDER_STYLE)
        self.temp_slider.setRange(Constants.BOOST_TEMPERATURE_MIN_CELSIUS, Constants.BOOST_TEMPERATURE_MAX_CELSIUS)
        self.temp_slider.setValue(Constants.DEFAULT_BOOST_TEMP_CELSIUS)
        self.temp_slider.setTickInterval(1)
        self.temp_slider.setPageStep(2)
        self.temp_slider.setSingleStep(1)
        self.temp_slider.setFixedHeight((parent.height() / 2) - 15)
        self.temp_slider.move(75, (parent.height() / 3))
        self.temp_slider.valueChanged.connect(lambda val: self.update_slider('temp', val))

        self.slider_label_te = QLabel('TEMPERATURE', self)
        self.slider_label_te.move(self.temp_slider.x() + 8, self.temp_slider.height() + self.temp_slider.y() + 13)
        self.value_label_te = QLabel(f'+{self.temp_slider.value()}°C',  self)
        self.value_label_te.setMinimumWidth(200)
        self.value_label_te.move(self.temp_slider.x() + 20, self.temp_slider.y() - 45)

        self.time_slider = QSlider(Qt.Vertical, self)
        self.time_slider.setStyleSheet(WIDE_SLIDER_STYLE)
        self.time_slider.setRange(Constants.BOOST_DURATION_MIN, Constants.BOOST_DURATION_MAX)
        self.time_slider.setValue(Constants.DEFAULT_BOOST_DURATION)
        self.time_slider.setTickInterval(1)
        self.time_slider.setPageStep(2)
        self.time_slider.setSingleStep(1)
        self.time_slider.setFixedHeight((parent.height() / 2) - 15)
        self.time_slider.move(self.temp_slider.x() * 4, self.temp_slider.y())
        self.time_slider.valueChanged.connect(lambda val: self.update_slider('time', val))
        self.slider_label_t = QLabel('TIME', self)
        self.slider_label_t.move(self.time_slider.x() + 33, self.time_slider.height() + self.time_slider.y() + 13)
        self.value_label_t = QLabel(f'+{self.time_slider.value()}s',  self)
        self.value_label_t.setMinimumWidth(200)
        self.value_label_t.move(self.time_slider.x() + 20, self.value_label_te.y())

        font = self.font()
        font.setPointSize(20)
        font.setBold(True)
        self.value_label_te.setFont(font)
        self.value_label_te.setStyleSheet('background: transparent;')
        self.value_label_t.setFont(font)
        self.value_label_t.setStyleSheet('background: transparent;')

    def reset(self):
        self.temp_slider.setValue(Constants.DEFAULT_BOOST_TEMP_CELSIUS)
        self.time_slider.setValue(Constants.DEFAULT_BOOST_DURATION)

    def update_slider(self, slider: str, val: int):
        client.device().send_boost_settings(slider, val)
        if slider == 'time':
            self.value_label_t.setText(f'+{val}s')
        else:
            self.value_label_te.setText(f'+{val}°C')

    def exit(self, _):
        control_center = self.parent()
        control_center.toggle_boost_settings(True)


class ColorWheel(ColorSlider):
    ASSET = 'color_wheel.png'
    last_selected = None

    def __init__(self, parent):
        super(ColorWheel, self).__init__(parent)
        self.setStyleSheet('background: transparent;')
        self.cursor_pixmap = QPixmap(':/themes/color_wheel_cursor.png').scaled(16, 16)
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
    animation_toggles = [False, False, False]  # pulse, rotating, disco
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

        self.cancel_button = ImageButton(':/icons/cancel.png', self, callback=self.exit)
        self.cancel_button.resize(48, 48)
        self.cancel_button.move(10, 6)

        anim_y = self.wheel.y() + self.wheel.height() + 25
        self.pulse_anim = ImageButton(':/icons/lantern_breathing.png', self, paint=False, size=(54, 54),
                                      callback=lambda: self.animation_toggle('PULSING'))
        self.pulse_anim.move(self.preview.x() + 50, anim_y)

        self.rotating_anim = ImageButton(':/icons/lantern_rotating.png', self, paint=False, size=(54, 54),
                                         callback=lambda: self.animation_toggle('ROTATING'))
        self.rotating_anim.move((self.pulse_anim.x() * 2) + 15, anim_y)

        self.disco_anim = ImageButton(':/icons/lantern_disco.png', self, paint=False, size=(54, 54),
                                      callback=lambda: self.animation_toggle('DISCO_MODE'))
        self.disco_anim.move((self.pulse_anim.x() * 3) + 25, anim_y)

        self.animations = [self.pulse_anim, self.rotating_anim, self.disco_anim]

    def exit(self, _):
        control_center = self.parent()
        lantern_set = bool(self.wheel.selected) or client.device().LANTERN_COLOR in LanternAnimation.all
        control_center.edit_lantern_settings(lantern_set, done=True)
        control_center.lantern_mode.ENABLED = lantern_set
        control_center.lantern_mode.recolor(forced=False)
        self.wheel.selected = None

    def animation_toggle(self, anim):
        others = []
        if anim == 'PULSING':
            others = [self.rotating_anim, self.disco_anim]
        elif anim == 'ROTATING':
            others = [self.pulse_anim, self.disco_anim]
        elif anim == 'DISCO_MODE':
            others = [self.pulse_anim, self.rotating_anim]

        control = list(set(self.animations) - set(others))[0]
        idx = self.animations.index(control)
        state = not self.animation_toggles[idx]
        self.animation_toggles[idx] = state

        # COLOR OUR TOGGLES CORRECTLY:
        for other in others:
            pixmap = other.alter_pixmap(other.path, other.iconSize(), paint=False, color=None)
            other.setIcon(QIcon(pixmap))

        pil_img = Image.fromqpixmap(control.PIXMAP)
        alpha_channel = pil_img.split()[-1]
        pil_img = ImageOps.invert(pil_img.convert('L'))
        pil_img.putalpha(alpha_channel)
        pixmap = control.PIXMAP = pil_img.convert('RGBA').toqpixmap()
        control.setIcon(QIcon(pixmap))
        # send the animation info
        client.device().send_lantern_animation(anim, state)


class ControlButton(ImageButton):
    ENABLED = False
    PATH = ':/icons/control_center_btn.png'

    def __init__(self, parent, btn_text, asset_fp, size, setting, special=False, **kwargs):
        self._callback = kwargs.pop('callback', None)
        super(ControlButton, self).__init__(self.PATH, parent, **kwargs)
        self._text = QLabel(btn_text, self)
        self._text.setFont(button_font)
        self._text.move(115, 45)
        self._text.update()
        self.btn_icon = ImageButton(asset_fp, self, size=size)
        self.btn_icon.move(65, 50)
        self.clicked.connect(self.on_click)
        self.setting_name = setting
        self.special = special

    def on_click(self, *, update_setting=True):
        self.ENABLED = not self.ENABLED
        if update_setting:
            settings.setValue(self.setting_name, self.ENABLED)

        forced = False
        if self._callback and update_setting:
            if self.special and (not self.ENABLED) and client.device().LANTERN_COLOR in LanternAnimation.all:
                forced = self.ENABLED = True

            self._callback(forced if forced else self.ENABLED)

        self.recolor(forced)

    def recolor(self, forced):
        color = QColor(255, 255, 255)
        if self.ENABLED or (self.special and forced):
            color = QColor(0, 0, 0)
            self._text.setStyleSheet('color: black;')
            pixmap = self.alter_pixmap(self.PATH, self.iconSize(), True, color=None)

        else:
            self._text.setStyleSheet('color: white;')
            pixmap = self.alter_pixmap(self.PATH, self.iconSize(), False, color=None)

        self.setIcon(QIcon(pixmap))
        pixmap = self.btn_icon.alter_pixmap(self.btn_icon.path, self.btn_icon.iconSize(), True, color)
        self.btn_icon.setIcon(QIcon(pixmap))


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
        self.boost_settings = BoostSettings(self)

        self.boost_controls = ImageButton(':/icons/boost_mode.png', self, paint=False,
                                          size=(54, 54), callback=self.toggle_boost_settings)
        self.boost_controls.move((parent.width() / 2), 150)

        self.power_button = ImageButton(':/icons/power_mode.png', self, paint=False,
                                        size=(54, 54), callback=lambda: client.device().send_command(DeviceCommands.MASTER_OFF))
        self.power_button.move((parent.width() / 2) + 70, 150)

        self.lantern_mode = ControlButton(self, 'LANTERN\nMODE', ':/icons/lantern_mode.png', (26, 42),
                                          'Modes/Lantern', paint=False, callback=self._lantern_callback, special=True)
        self.lantern_mode.move(self.boost_controls.x() - 57, self.power_button.y() + 45)
        self.lantern_mode.btn_icon.move(65, 45)

        self.ready_mode = ControlButton(self, 'READY\nMODE', ':/icons/ready_mode.png', (26, 36),
                                        'Modes/Ready', paint=False)  # callback not needed here
        self.ready_mode.move(self.boost_controls.x() - 57, self.lantern_mode.y() + 100)

        self.stealth_mode = ControlButton(self, 'STEALTH\nMODE', ':/icons/stealth_mode.png', (42, 30),
                                          'Modes/Stealth', paint=False, callback=self.set_stealth_mode)
        self.stealth_mode.move(self.boost_controls.x() - 57, self.ready_mode.y() + 100)
        self.stealth_mode.btn_icon.move(55, 50)

        self.lantern_brightness = QSlider(Qt.Vertical, self)
        self.lantern_brightness.setStyleSheet(WIDE_SLIDER_STYLE)
        self.lantern_brightness.setRange(Constants.BRIGHTNESS_MIN, Constants.BRIGHTNESS_MAX)
        self.lantern_brightness.setValue(Constants.BRIGHTNESS_MIN)
        self.lantern_brightness.setTickInterval(1)
        self.lantern_brightness.setPageStep(5)
        self.lantern_brightness.setSingleStep(1)
        self.lantern_brightness.setFixedHeight((parent.height() / 2) - 15)
        self.lantern_brightness.move(75, (parent.height() / 4) - 25)
        self.lantern_brightness.valueChanged.connect(client.send_lantern_brightness)

        self.CONTROLS = [self.lantern_mode, self.ready_mode, self.stealth_mode]

    def _lantern_callback(self, enabled):
        if enabled is False and (bool(self.lantern_settings.wheel.selected) or
                                 client.device().LANTERN_COLOR in LanternAnimation.all):
            enabled = True

        self.edit_lantern_settings(enabled)

    def edit_lantern_settings(self, enabled, done=False):
        client.device().send_lantern_status(enabled)
        if enabled and not done:
            self.parent().ctrl_center_btn.hide()
            self.lantern_settings.show()
            self.lantern_settings.raise_()
        else:
            self.parent().ctrl_center_btn.show()
            self.lantern_settings.lower()
            self.lantern_settings.hide()

    def toggle_boost_settings(self, done=False):
        enabled = not self.boost_settings.isVisible()
        print(f'toggle_boost_settings {enabled} {done}')
        client.device().send_lantern_status(enabled)
        if enabled and not done:
            self.parent().ctrl_center_btn.hide()
            self.boost_settings.show()
            self.boost_settings.raise_()
        else:
            self.parent().ctrl_center_btn.show()
            self.boost_settings.lower()
            self.boost_settings.hide()

    @staticmethod
    def set_stealth_mode(val):
        client.device().stealth_mode = val
