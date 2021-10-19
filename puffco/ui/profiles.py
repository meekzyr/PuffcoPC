from asyncio import ensure_future
from PyQt5.QtWidgets import QFrame
from PyQt5.QtGui import QPixmap

from .elements import ProfileButton


class HeatProfiles(QFrame):
    def __init__(self, parent):
        super(HeatProfiles, self).__init__(parent)
        self.setStyleSheet('background: transparent;')
        self.setVisible(False)
        self.profile_buttons = {}
        self.create_profile_labels()

    def create_profile_labels(self):
        if self.profile_buttons:
            return

        geom = [30, 0, self.parent().width() - 65, 120]
        for i in range(0, 4):
            geom[1] += geom[3] + 30  # offset 30px
            self.profile_buttons[i] = ProfileButton(self, QPixmap(':/assets/data-gradient.png'), geom)

        self.profile_buttons[0].clicked.connect(lambda: ensure_future(self.preheat(0)).done())
        self.profile_buttons[1].clicked.connect(lambda: ensure_future(self.preheat(1)).done())
        self.profile_buttons[2].clicked.connect(lambda: ensure_future(self.preheat(2)).done())
        self.profile_buttons[3].clicked.connect(lambda: ensure_future(self.preheat(3)).done())

    async def preheat(self, profile_num):
        profile_info = self.parent().PROFILES[profile_num]
        await client.change_profile(profile_num, current=True)
        await client.preheat()

    async def fill(self):
        self.setUpdatesEnabled(False)

        for profile in self.parent().PROFILES:
            label = self.profile_buttons[profile.idx]
            label.set_profile_name(profile.name)
            label.set_temperature(f'{profile.temperature_f} °F')
            label.set_duration(f'{profile.duration // 60}:{str(profile.duration % 60).zfill(2)}')
            label.set_pixmap_color(profile.color)

        self.setUpdatesEnabled(True)
