from asyncio import ensure_future
from PyQt5.QtWidgets import QFrame, QLabel
from PyQt5.QtGui import QPixmap, QFont

from .elements import ProfileButton
from .profile_window import ProfileWindow


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
            self.profile_buttons[i] = ProfileButton(self, i, QPixmap(':/assets/data-gradient.png'), geom,
                                                    callback=self.select_profile)
            geom[1] += geom[3] + 20  # offset 20px

    def select_profile(self, profile_num):
        if self.active_profile:
            self.active_profile.destroy(True, True)
            self.active_profile = None

        profile = self.parent().PROFILES[profile_num]
        ensure_future(client.change_profile(profile_num, current=True)).done()
        self.active_profile = ProfileWindow(self.parent(), profile_num, profile.name, profile.temperature_f,
                                            profile.duration, tuple(profile.color))
        self.active_profile.show()

    async def fill(self):
        self.setUpdatesEnabled(False)

        for profile in self.parent().PROFILES:
            label = self.profile_buttons[profile.idx]
            label.set_profile_name(profile.name)
            label.set_temperature(f'{profile.temperature_f} °F')
            label.set_duration(f'{profile.duration // 60}:{str(profile.duration % 60).zfill(2)}')
            label.set_pixmap_color(profile.color)
            label.raise_()

        self.setUpdatesEnabled(True)
