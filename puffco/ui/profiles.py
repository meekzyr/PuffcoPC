from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtWidgets import QFrame, QLabel

from puffco.bluetooth import ensure_future
from . import LanternAnimation
from .elements import ProfileButton
from .profile_window import ProfileWindow


class Profile:
    def __init__(self, idx, name, temperature, time, color, color_bytes):
        self.idx = idx
        self.name = name
        self.temperature = temperature
        self.temperature_f = round(9.0 / 5.0 * temperature + 32)
        self.duration = time
        self.color = color
        self.color_bytes = color_bytes

    @property
    def rainbow(self):
        return (bytes(self.color_bytes) == LanternAnimation.DISCO_MODE) or self.color_bytes[3] == 1

    def __str__(self):
        return str(self.__dict__)


class HeatProfiles(QFrame):
    def __init__(self, parent):
        super(HeatProfiles, self).__init__(parent)
        self.setMinimumSize(parent.width(), parent.height() - 135)
        self.move(0, 60)
        self.lower()
        self.setStyleSheet('background: transparent;')
        self.heading = QLabel('HEAT PROFILES', self)
        font = QFont(self.font().family(), 24)
        font.setStretch(font.Unstretched * 1.25)
        self.heading.setFont(font)
        self.heading.adjustSize()
        self.heading.move(150, 5)
        self.active_profile = None

        self.setVisible(False)
        self.profile_buttons = {}
        self.create_profile_labels()

    def create_profile_labels(self):
        if self.profile_buttons:
            return

        geom = [30, 70, self.parent().width() - 65, 110]  # x, y, w, h
        for i in range(0, 4):
            self.profile_buttons[i] = ProfileButton(self, i, geom, callback=self.select_profile)
            geom[1] += geom[3] + 20  # offset 20px

    def select_profile(self, profile_num):
        if self.active_profile:
            self.active_profile.destroy(True, True)
            self.active_profile = None

        profile = self.parent().PROFILES[profile_num]
        ensure_future(client.device().change_profile(profile_num, current=True))
        self.active_profile = ProfileWindow(self.parent(), profile_num, profile.name, profile.temperature_f,
                                            profile.duration, tuple(profile.color), profile.rainbow)
        self.active_profile.show()

    async def retrieve_profiles(self):
        root = self.parent()
        device = root.bluetooth.device()
        current_profile_name = await device.profile_name

        reset_idx = None
        # loop through the 4 profiles; fetching and storing the data for each of them
        for i in range(0, 4):
            await device.change_profile(i)

            name = await device.profile_name
            if current_profile_name == name:
                reset_idx = i

            color_bytes = await device.profile_color
            _temp = await device.profile_temp
            _time = await device.profile_time
            root.PROFILES.append(Profile(i, name, _temp, _time, color_bytes[:3], color_bytes))

        # reset the profile back to where it was
        if reset_idx is not None:
            await device.change_profile(reset_idx, current=True)

        if root.profiles.isVisible():
            root.profiles.setVisible(False)

        await self.fill()
        root.profiles_button.setDisabled(False)

    async def fill(self, idx=None):
        self.setUpdatesEnabled(False)

        for profile in self.parent().PROFILES:
            if idx is not None and profile.idx != idx:
                continue

            label = self.profile_buttons[profile.idx]
            label.set_profile_name(profile.name)
            label.set_temperature(f'{profile.temperature_f} °F')
            label.set_duration(f'{profile.duration // 60}:{str(profile.duration % 60).zfill(2)}')
            if profile.rainbow:
                label.pix_asset = theme.RAINBOW_PROFILE
                label.color = None
                label._pixmap = QPixmap(label.pix_asset)
                label.set_pixmap_color((0, 0, 0))
            else:
                if label.pix_asset != theme.HOME_DATA:
                    label.pix_asset = theme.HOME_DATA
                    label._pixmap = QPixmap(label.pix_asset)
                    label.update()

                label.set_pixmap_color(profile.color)
            label.raise_()

        self.setUpdatesEnabled(True)
