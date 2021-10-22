from asyncio import ensure_future
from PyQt5.QtWidgets import QMainWindow, QLabel, QFrame, QSlider, QLineEdit
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QFont, QMouseEvent, QPixmap
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
    def __init__(self, parent, title, s_min: int = 0, s_max: int = 0, value: int = 0, *, color=False, current='white'):
        self._title = title
        self._window = parent.parent()
        super(ProfileSlider, self).__init__(parent)
        self.setStyleSheet('background: transparent;')
        self.setMinimumSize(parent.width(), 80)
        self.setFixedHeight(50)
        self.title = QLabel(title, self)
        self.title.setFont(QFont(self.font().defaultFamily(), 12))
        self.title.adjustSize()
        self.title.move(0, 0)
        if not color:
            self.slider = QSlider(Qt.Horizontal, self)
            self.slider.setRange(s_min, s_max)
            self.slider.setValue(value or s_min)
            self.slider.setTickInterval(1)
            self.slider.setSingleStep(1)
            self.slider.setFixedWidth(300)
            self.slider.move(50, self.title.height() + 15)
            self.slider.valueChanged.connect(self.value_changed)
        else:
            self.preview = QLabel('', self)
            self.preview.setFixedSize(24, 16)
            self.preview.move(self.title.width() + 10, 2)
            self.preview.setStyleSheet(f'border: 1px solid white;'
                                       f'background-color: rgb{current};')

            self.slider = ColorSlider(self)
            self.slider.move(50, self.title.height() + 15)

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
        self.temperature_control = ProfileSlider(self, 'TEMPERATURE', s_min=200, s_max=620,
                                                 value=temperature)

        # official app Duration range (15s - 120s)
        self.duration_control = ProfileSlider(self, 'DURATION', s_min=15, s_max=120, value=duration)
        self.duration_control.move(0, 70)

        self.color_control = ProfileSlider(self, 'COLOR', color=True, current=color)
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
    SIZE = QSize(480, 480)
    PROFILE_NAME_MAX_LENGTH = 31

    def __init__(self, parent, idx=0, _name='ALN TEST', _temp=475, raw_dur=15, _color=None):
        super(ProfileWindow, self).__init__(parent)
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
        self.p_name.move(190, 40)
        self.p_name.setReadOnly(True)
        self.p_name.textEdited.connect(self.uppercase_text)

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
        self.start_button.move(190, 180)

        self.temperature = QLabel(self._temp, self)
        self.temperature.setFixedSize(150, 80)
        font.setWeight(QFont.Weight.ExtraBold)
        font.setPointSize(28)
        font.setStretch(QFont.Unstretched)
        self.temperature.setFont(font)
        self.temperature.move(190, 320)
        self.temperature.setStyleSheet('background: transparent;')

        self.duration = QLabel(self._dur, self)
        self.duration.setStyleSheet('background: transparent;')
        self.duration.setFont(QFont('Slick', 12))
        self.duration.adjustSize()
        self.duration.move(self.temperature.x() + 10, self.temperature.y() + 60)

        self.controls = EditControls(self, idx, _temp, raw_dur, _color)
        self.controls.move(self.controls.x(), self.controls.y() - 60)
        self.controls.hide()

    def uppercase_text(self, text):
        self.p_name.setText(str(text[:self.PROFILE_NAME_MAX_LENGTH]).upper())
        self.p_name.adjustSize()

    def start(self):
        ensure_future(client.preheat()).done()

    def done(self, confirm=False):
        if not confirm:
            self.p_name.setText(self._name)
            self.temperature.setText(self._temp)
            self.duration.setText(self._dur)
        else:
            ensure_future(self.controls.write_to_device(self._name, self.r_temp, self.r_dur, self._color)).done()
            print('successfully wrote changes to profile')

        self.p_name.setReadOnly(True)
        self.start_button.show()
        self.edit_button.show()
        self.confirm_edit_button.hide()
        self.cancel_edit_button.hide()
        self.temperature.move(190, 360)
        self.duration.move(self.temperature.x() + 10, self.temperature.y() + 60)
        self.controls.hide()

    def edit_clicked(self):
        self.p_name.setReadOnly(False)
        self.start_button.hide()
        self.edit_button.hide()
        self.confirm_edit_button.show()
        self.cancel_edit_button.show()
        self.temperature.move(190, 120)
        self.controls.show()
        self.duration.move(self.temperature.x() + 10, self.temperature.y() + 60)
