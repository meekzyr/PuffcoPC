from asyncio import ensure_future
from PyQt5.QtWidgets import QMainWindow, QLabel, QFrame, QSlider, QLineEdit
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QFont, QMouseEvent, QPixmap, QPainter, QColor
from PIL import Image

from .elements import WhiteImageButton


class ColorSlider(QLabel):
    selecting = False
    selected = None

    def __init__(self, parent):
        super(ColorSlider, self).__init__('', parent)
        self.setMouseTracking(True)
        pixmap = QPixmap(':assets/rainbow_slider.png')
        self.image = Image.fromqpixmap(pixmap).convert('RGB')
        self.setPixmap(pixmap)
        self.setFixedSize(self.pixmap().size())

    def mouseMoveEvent(self, ev: QMouseEvent) -> None:
        if not self.selecting:
            return

        x = ev.x()
        y = ev.y()
        if y >= self.image.height:
            y = min(2, y)

        if x >= self.image.width:
            x = self.image.width - 1

        self.selected = self.image.getpixel((max(0, x), max(0, y)))
        self.parent().preview.setStyleSheet(f'background: rgb{self.selected};'
                                            f'border: 1px solid white;')

    def mouseReleaseEvent(self, ev: QMouseEvent) -> None:
        if ev.button() != Qt.LeftButton:
            return

        self.selecting = False

    def mousePressEvent(self, ev: QMouseEvent) -> None:
        if ev.button() != Qt.LeftButton:
            return

        self.selecting = True

    def value(self):
        return self.selected


class ProfileSlider(QFrame):
    def __init__(self, parent, title: str, asset: str, _min: int = 0, _max: int = 0, value: int = 0, color=False, current='white'):
        self._title = title
        self._window = parent.parent()
        super(ProfileSlider, self).__init__(parent)
        self.setStyleSheet('background: transparent;')
        self.setMinimumSize(parent.width(), 90)
        self.setFixedHeight(60)
        self.title = QLabel(title, self)
        self.title.setFont(QFont(self.font().defaultFamily(), 12))
        self.title.adjustSize()
        self.title.move(0, 0)

        if not color:
            self.slider = QSlider(Qt.Horizontal, self)
            self.slider.setRange(_min, _max)
            self.slider.setValue(value or _min)
            self.slider.setTickInterval(1)
            self.slider.setSingleStep(1)
            self.slider.setFixedWidth(306)
            self.slider.move(50, self.title.height() + 15)
            self.slider.valueChanged.connect(self.value_changed)

            self.icon = WhiteImageButton(asset, self, size=(24, 24))
            self.icon.setDisabled(True)
            self.icon.move(5, 30)
        else:
            self.preview = QLabel('', self)
            self.preview.setFixedSize(24, 18)
            self.preview.move(self.title.x() + 5, self.title.y() + 27)
            self.preview.setStyleSheet(f'border: 1px solid white;'
                                       f'background-color: rgb{current};')

            self.slider = ColorSlider(self)
            self.slider.move(52, self.title.height() + 15)

    @property
    def value(self):
        return self.slider.value()

    def value_changed(self, val):
        widget = None
        if self._title == 'TEMPERATURE':
            widget = self._window.temperature
            val = f'{val} °F'
        elif self._title == 'DURATION':
            widget = self._window.duration
            minutes, seconds = divmod(val, 60)
            val = f'{str(minutes).zfill(2)}:{str(seconds).zfill(2)}'

        if widget:
            widget.setText(val)
            widget.update()


class EditControls(QFrame):
    def __init__(self, parent, idx, temperature, duration, color):
        self._idx = idx
        super(EditControls, self).__init__(parent)
        self.setStyleSheet('background: transparent;')
        self.setMinimumSize(parent.size())
        self.move(30, 320)

        # official app Fahrenheit range (400 - 620)
        self.temperature_control = ProfileSlider(self, 'TEMPERATURE',
                                                 ':/assets/icon_thermometer.png',
                                                 _min=200, _max=620,
                                                 value=temperature)
        self.temperature_control.icon.move(9, self.temperature_control.icon.y())

        # official app Duration range (15s - 120s)
        self.duration_control = ProfileSlider(self, 'DURATION',
                                              ':/assets/icon_clock.png',
                                              _min=15, _max=120, value=duration)
        self.duration_control.move(0, 70)

        self.color_control = ProfileSlider(self, 'COLOR',
                                           ':/assets/icon_clock.png',
                                           color=True, current=color)
        self.color_control.move(0, 140)

    async def write_to_device(self, old_name, old_temp, old_dur, old_color):
        home = self.parent().parent()
        profile = home.PROFILES[self._idx]
        new_name = self.parent().p_name.text()
        if new_name and old_name != new_name:
            profile.name = new_name
            self.setWindowTitle(new_name)
            await client.set_profile_name(new_name)

        new_temp = self.temperature_control.value
        if new_temp and old_temp != new_temp:
            profile.temperature_f = new_temp
            # new temp is in fahrenheit, convert to celsius
            profile.temperature = round((new_temp - 32) * 0.5556, 2)
            await client.set_profile_temp(profile.temperature)

        new_dur = self.duration_control.value
        if old_dur and new_dur != old_dur:
            profile.duration = new_dur
            await client.set_profile_time(new_dur)

        new_color = self.color_control.value
        if new_color is not None and new_color != old_color:
            # i have NO idea what all the individual bytes attribute to
            profile.color_bytes = list(new_color) + profile.color_bytes[3:]
            profile.color = new_color
            await client.set_profile_color(profile.color_bytes)

        await home.profiles.fill()


class ProfileWindow(QMainWindow):
    TEMP_DEFAULT_XY = (200, 320)
    SIZE = QSize(480, 480)
    PROFILE_NAME_MAX_LENGTH = 31
    started = False
    verified = False

    def __init__(self, parent, idx=0, _name='ALN TEST', _temp=475, raw_dur=15, _color=None):
        super(ProfileWindow, self).__init__(parent)
        self.idx = idx
        self._name = _name
        self._temp = f'{_temp} °F'
        self.r_temp = _temp
        self.r_dur = raw_dur
        m, s = divmod(raw_dur, 60)
        self._dur = f'{str(m).zfill(2)}:{str(s).zfill(2)}'
        self._color = _color
        self.setWindowTitle(_name)
        self.setFixedSize(self.SIZE)
        font = QFont(self.font().family(), 20)
        font.setStretch(QFont.Unstretched * 1.5)

        self.p_name = QLineEdit('', self)
        self.p_name.setFont(font)
        self.p_name.setText(_name)
        self.p_name.adjustSize()
        self.p_name.move(196, 36)
        self.p_name.setReadOnly(True)
        self.p_name.textEdited.connect(self.uppercase_text)
        self.p_name.selectionChanged.connect(lambda: self.p_name.setSelection(0, 0))

        self.edit_button = WhiteImageButton(':/assets/iconmore.png', self, callback=self.edit_clicked)
        self.edit_button.resize(48, 48)
        self.edit_button.move(self.width() - self.edit_button.width() - 10, 30)

        self.cancel_edit_button = WhiteImageButton(':/assets/iconclose.png', self, callback=self.done)
        self.cancel_edit_button.resize(48, 48)
        self.cancel_edit_button.move(10, self.edit_button.y())
        self.cancel_edit_button.hide()

        self.confirm_edit_button = WhiteImageButton(':/assets/iconcheck.png', self,
                                                    callback=lambda: self.done(confirm=True))
        self.confirm_edit_button.resize(48, 48)
        self.confirm_edit_button.move(self.edit_button.pos())
        self.confirm_edit_button.hide()

        self.start_button = WhiteImageButton(':/icon/puffco-logo.png', self, callback=self.start)
        self.start_button.resize(64, 64)
        self.start_button.move(207, 180)
        self.cancel_button = WhiteImageButton(':/assets/iconclose.png', self, callback=lambda: self.done(cancel=True))
        self.cancel_button.resize(48, 48)
        self.cancel_button.move(210, 320)
        self.cancel_button.hide()

        self.start_text = QLabel('START', self)
        self.start_text.setScaledContents(True)
        self.start_text.setFixedSize(36, 24)
        self.start_text.adjustSize()
        self.start_text.setStyleSheet('background: transparent;')
        self.start_text.move(self.start_button.x() + 13, self.start_button.y() +
                             self.start_button.iconSize().height() + 5)

        self.cancel_text = QLabel('CANCEL', self)
        self.cancel_text.setScaledContents(True)
        self.cancel_text.setFixedSize(48, 24)
        self.cancel_text.setStyleSheet('background: transparent;')
        self.cancel_text.move(self.cancel_button.x(), self.cancel_button.y() +
                              self.cancel_button.iconSize().height() + 5)
        self.cancel_text.hide()

        self.temperature = QLabel(self._temp, self)
        self.temperature.setFixedSize(150, 80)
        font.setWeight(QFont.Weight.ExtraBold)
        font.setPointSize(28)
        font.setStretch(QFont.Unstretched)
        self.temperature.setFont(font)
        self.temperature.move(*self.TEMP_DEFAULT_XY)
        self.temperature.setStyleSheet('background: transparent;')

        self.duration = QLabel(self._dur, self)
        self.duration.setStyleSheet('background: transparent;')
        self.duration.setFont(QFont('Slick', 12))
        self.duration.adjustSize()
        self.duration.move(self.temperature.x() + 15, self.temperature.y() + 60)

        self.controls = EditControls(self, idx, _temp, raw_dur, _color)
        self.controls.move(self.controls.x() + 32, self.controls.y() - 60)
        self.controls.hide()

        # todo: timer countdown
        # todo: add boost time + temp buttons

    def uppercase_text(self, text):
        self.p_name.setText(str(text[:self.PROFILE_NAME_MAX_LENGTH]).upper())
        self.p_name.adjustSize()

    def update_temp_reading(self, text):
        self.temperature.setText(text)

    def start(self, *, send_command=True):
        if self.started:
            return

        self.start_text.hide()
        self.start_button.hide()
        self.cancel_button.show()
        self.cancel_text.show()
        self.edit_button.hide()

        self.temperature.move(200, 183)
        self.duration.move(self.temperature.x() + 15, self.temperature.y() + 60)
        self.started = True
        if send_command:
            ensure_future(client.preheat()).done()

    def cycle_finished(self):
        self.started = False
        self.verified = False
        self.start_text.show()
        self.start_button.show()
        self.cancel_button.hide()
        self.cancel_text.hide()
        self.edit_button.show()
        self.temperature.move(*self.TEMP_DEFAULT_XY)
        self.duration.move(self.temperature.x() + 10, self.temperature.y() + 60)

    def done(self, confirm=False, cancel=False):
        if not confirm:
            self.p_name.setText(self._name)
            self.temperature.setText(self._temp)
            self.duration.setText(self._dur)
        else:
            ensure_future(self.controls.write_to_device(self._name, self.r_temp, self.r_dur, self._color)).done()
            print('successfully wrote changes to profile')

        if cancel:
            ensure_future(client.preheat(cancel=True)).done()

        self.started = False
        self.p_name.selectionChanged.connect(lambda: self.p_name.setSelection(0, 0))
        self.p_name.setReadOnly(True)
        self.start_text.show()
        self.start_button.show()
        self.cancel_button.hide()
        self.cancel_text.hide()
        self.edit_button.show()
        self.confirm_edit_button.hide()
        self.cancel_edit_button.hide()
        self.temperature.move(*self.TEMP_DEFAULT_XY)
        self.duration.move(self.temperature.x() + 10, self.temperature.y() + 60)
        self.controls.hide()

    def edit_clicked(self):
        self.p_name.selectionChanged.disconnect()
        self.p_name.setReadOnly(False)
        self.start_text.hide()
        self.start_button.hide()
        self.edit_button.hide()
        self.confirm_edit_button.show()
        self.cancel_edit_button.show()
        self.temperature.move(190, 120)
        self.controls.show()
        self.duration.move(self.temperature.x() + 10, self.temperature.y() + 60)
