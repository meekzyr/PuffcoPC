from asyncio import futures, ensure_future, sleep
from PyQt5.QtCore import QSize, QMetaObject
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import QPushButton, QMainWindow, QLabel

from bleak import BleakError, BleakScanner

from puffco.btnet import Characteristics
from .elements import WhiteImageButton
from .homescreen import HomeScreen
from .profiles import HeatProfiles
from .settings import Settings


class Profile:
    def __init__(self, idx, name, temperature, time, color, color_bytes):
        self.idx = idx
        self.name = name
        self.temperature = temperature
        self.temperature_f = round((temperature * 1.8) + 32)
        self.duration = time
        self.color = color
        self.color_bytes = color_bytes

    def __str__(self):
        return str(self.__dict__)


class PuffcoMain(QMainWindow):
    PROFILES = []
    current_tab = 'home'
    SIZE = QSize(480, 844)

    def __init__(self, client):
        self._client = client
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

        self.settings_window = Settings(self)
        self.settings = WhiteImageButton(':/assets/assets/icon-settings.png', self, callback=self.display_settings)
        self.settings.move(self.width() - 70, 20)

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
        self.profilesButton.setDisabled(True)

        divider = QLabel('', self)
        divider.setPixmap(QPixmap(':/assets/menu_separator.png'))
        divider.setScaledContents(True)
        divider.setGeometry(-92, self.homeButton.y() - 4, 573, 4)
        divider.setStyleSheet('background: transparent;')

        self.setCentralWidget(self.home)
        # draw up the home screen upon launching the app
        self.home.setVisible(True)
        self.show()

        #self.settings.raise_()

        QMetaObject.connectSlotsByName(self)

    def display_settings(self, *args):
        print('hey', args)

        self.settings_window.show()

    def closeEvent(self, event):
        loop.stop()
        event.accept()

    def show_tab(self, frame):
        is_home = frame == self.home
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
            # no connect (typically happens when reading a characteristic in the same frame as establishing connection)
            return self.show_tab(frame)

        frame.show()
        frame.setVisible(True)
        other.hide()  # hide the other frame to prevent element bleed
        other.setVisible(False)

    async def connect(self, *, retry=False):
        if self._client.address == '':
            scanner = BleakScanner()
            devices_found = await scanner.discover()
            for device in devices_found:
                service_uuids = device.metadata.get('uuids')
                device_mac_address = device.address
                if device_mac_address in self._client.attempted_devices:
                    print(f'skipping over {device.name} ({device_mac_address}, already failed to connect before')
                    continue

                if Characteristics.SERVICE_UUID in service_uuids or device.address.startswith('84:2E:14:'):
                    print('Potential Puffco Product', device.address, device.name)
                    self._client.address = device.address
                    break

            if self._client.address == '':
                return await self.connect(retry=True)

        # TODO: fix disconnect callback spam
        #self._client.set_disconnected_callback(lambda *args: ensure_future(self._on_disconnect()).done())

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
            print('Retrying..')
            return await self.connect(retry=True)

        print('Connected!')
        return connected

    async def _on_disconnect(self):
        await self.home.reset()
        if not self.isVisible():
            self.show()`

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
            color_bytes = await self._client.get_profile_color()
            time = await self._client.get_profile_time()

            self.PROFILES.append(Profile(i, name, temp, time, color_bytes[:3], color_bytes))
            await sleep(0.1)  # short delay to prevent incorrect profile colors

        # reset the profile back to where it was
        if reset_idx is not None:
            await self._client.change_profile(reset_idx)

        await self.profiles.fill()
        await self.home.fill(from_callback=True)
        if not self.isVisible():
            self.show()

        self.profilesButton.setDisabled(False)
