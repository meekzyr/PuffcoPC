import builtins
from asyncio import futures, ensure_future
from PyQt5.QtCore import QSize, QMetaObject, QPoint
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor
from PyQt5.QtWidgets import QPushButton, QMainWindow, QLabel

from bleak import BleakError
from puffco.btnet.client import PuffcoBleakClient
from .homescreen import HomeScreen
from .profiles import HeatProfiles


class Profile:
    def __init__(self, idx, name, temperature, time, color):
        self.idx = idx
        self.name = name
        self.temperature = temperature
        self.temperature_f = round((temperature * 1.8) + 32)
        self.duration = time
        self.color = color


class PuffcoMain(QMainWindow):
    PROFILES = []
    initial = True
    current_tab = 'home'
    SIZE = QSize(480, 844)

    def __init__(self, mac_address: str, loop):
        self._client = builtins.client = PuffcoBleakClient(mac_address)
        self._loop = loop
        super(PuffcoMain, self).__init__(parent=None)
        self.setWindowTitle("Puffco Connect (PC)")
        self.setMinimumSize(self.SIZE)
        self.setMaximumSize(self.SIZE)
        self.setMouseTracking(True)
        self.setWindowIcon(QIcon(":/icon/favicon.ico"))
        self.setStyleSheet("background-image: url(:/assets/background.png);\n"
                           "color: rgb(255, 255, 255);\n"
                           "border: 0px;")

        self.puffcoIcon = QLabel('', self)
        self.puffcoIcon.setGeometry(210, 5, 64, 64)
        self.puffcoIcon.setStyleSheet("image: url(:/icon/puffco-logo.png);\n"
                                      "background: transparent;\n")

        self.home = HomeScreen(self)
        self.profiles = HeatProfiles(self)
        self.profiles.setGeometry(self.geometry())
        self.homeButton = QPushButton('MY PEAK', self)
        btn_height = 70
        self.homeButton.setGeometry(0, self.height() - btn_height, self.width() / 2, btn_height)  # x, y, w, h
        self.homeButton.clicked.connect(lambda: self.show_tab(self.home))

        self.profilesButton = QPushButton('HEAT PROFILES', self)
        self.profilesButton.setGeometry(self.homeButton.width() + 2, self.homeButton.y(),
                                        self.homeButton.width() - 2, self.homeButton.height())
        self.profilesButton.clicked.connect(lambda: self.show_tab(self.profiles))

        divider = QLabel('', self)
        divider.setPixmap(QPixmap(':/assets/menu-separator.png'))
        divider.setScaledContents(True)
        divider.setGeometry(-92, self.homeButton.y() - 4, 573, 4)
        divider.setStyleSheet('background: transparent;')

        x = QPainter()
        x.setPen(QColor(255, 255, 255))
        x.drawPoints(QPoint(210, 50), QPoint(210, 90))
        x.end()
        self.setCentralWidget(self.home)
        # draw up the home screen upon launching the app
        self.home.setVisible(True)
        self.show()

        QMetaObject.connectSlotsByName(self)

    def show_tab(self, frame):
        is_home = frame == self.home
        print('show_tab', frame, is_home)
        if (is_home and self.current_tab == 'home') or (self.current_tab == 'profiles' and not is_home):
            return

        self.current_tab = 'home' if is_home else 'profiles'
        other = self.profiles if is_home else self.home

        self.homeButton.setDown(is_home)
        self.profilesButton.setDown(not is_home)

        # update the data
        try:
            fetch_task = ensure_future(frame.fill())
            fetch_task.done()
        except BleakError:
            # no connect (typically happens when reading a characteristic in the same frame as establishing connection),
            return self.show_tab(frame)

        frame.show()
        frame.setVisible(True)
        other.hide()  # hide the other frame to prevent element bleed
        other.setVisible(False)

    async def connect(self, *, retry=False):
        if self.initial:
            self._client.set_disconnected_callback(lambda *args: ensure_future(self._on_disconnect()).done())
            self.initial = False

        if retry:
            try:
                await self._client.unpair()
            except AttributeError:
                # was not paired to begin with:
                pass

            await self._client.disconnect()

        connected = False
        try:
            connected = await self._client.connect(timeout=3, use_cached=not retry)
            await self._on_connect()
        except futures.TimeoutError as e:  # could not connect to device
            print('timeout error', e)
        except BleakError as e:  # could not find device
            print('bleak error', e)

        if self.home.ui_connectStatus.text() != 'DISCONNECTED' and not connected:
            self.home.ui_connectStatus.setText('DISCONNECTED')
            self.home.ui_connectStatus.setStyleSheet(f'color: red;')

        if connected:
            await self._client.pair()
        else:
            print('retrying..')
            return await self.connect(retry=True)

        return connected

    async def _on_disconnect(self):
        await self.home.reset()
        if not self.isVisible():
            self.show()

        print('lost connection to device, attempting to reconnect...')
        await self.connect(retry=True)

    async def _on_connect(self):
        current_profile_name = await self._client.get_profile_name()

        reset_idx = None
        # loop through the 4 profiles; fetching and storing the data for each of them
        for i in range(0, 4):
            await self._client.change_profile(i)
            name = await self._client.get_profile_name()
            if current_profile_name == name:
                reset_idx = i

            temp = await self._client.get_profile_temp()
            color = await self._client.profile_color_as_rgb(current_profile=i)
            time = await self._client.get_profile_time()

            self.PROFILES.append(Profile(i, name, temp, time, color))

        # reset the profile back to where it was
        if reset_idx is not None:
            await self._client.change_profile(reset_idx)

        if self.current_tab != 'home':
            self.show_tab(self.home)
        await self.profiles.fill()
        await self.home.fill(from_callback=True)
        if not self.isVisible():
            self.show()
