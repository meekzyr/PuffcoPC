import builtins

from asyncio import futures, ensure_future, sleep
from PyQt5.QtCore import QSize, QMetaObject
from PyQt5.QtGui import QIcon, QPixmap, QColor
from PyQt5.QtWidgets import QPushButton, QMainWindow, QLabel

from bleak import BleakError, BleakScanner

from puffco.btnet import Characteristics
from .themes import DEVICE_THEME_MAP
from .elements import ImageButton
from .homescreen import HomeScreen
from .profiles import HeatProfiles
from .control_center import ControlCenter


class Profile:
    def __init__(self, idx, name, temperature, time, color, color_bytes):
        self.idx = idx
        self.name = name
        self.temperature = temperature
        self.temperature_f = round(9.0/5.0 * temperature + 32)
        self.duration = time
        self.color = color
        self.color_bytes = color_bytes

    def __str__(self):
        return str(self.__dict__)


class PuffcoMain(QMainWindow):
    RETRIES = 0
    PROFILES = []
    current_tab = 'home'
    SIZE = QSize(480, 720)

    def __init__(self, client):
        self._client = client
        super(PuffcoMain, self).__init__(parent=None)
        self.setWindowTitle("Puffco Connect (PC)")
        self.setMinimumSize(self.SIZE)
        self.setMaximumSize(self.SIZE)
        self.setMouseTracking(True)
        self.setWindowIcon(QIcon(":/misc/puffco.ico"))
        self.setStyleSheet(f"background-image: url({theme.BACKGROUND});\n"
                           f"color: rgb{theme.TEXT_COLOR};\n"
                           "border: 0px;")

        self.puffcoIcon = ImageButton(':/misc/logo.png', self, size=(64, 64))
        self.puffcoIcon.move(210, 0)

        self.control_center = ControlCenter(self)
        self.ctrl_center_btn = ImageButton(':/icons/control_center.png', self,
                                           callback=self.toggle_ctrl_center, size=(36, 36),
                                           color=QColor(*theme.TEXT_COLOR))
        self.ctrl_center_btn.move(self.width() - 70, 10)
        self.ctrl_center_btn.setDisabled(True)

        self.home = HomeScreen(self)

        self.homeButton = QPushButton('MY PEAK', self)
        self.homeButton.setGeometry(0, self.height() - 70, self.width() / 2, 70)
        self.homeButton.clicked.connect(lambda: self.show_tab(self.home))

        self.profiles = HeatProfiles(self)
        self.profiles.lower()
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

        # draw up the home screen upon launching the app
        self.home.setVisible(True)
        self.show()

        QMetaObject.connectSlotsByName(self)

    def toggle_ctrl_center(self):
        if self.control_center.isHidden():
            self.control_center.show()
        else:
            self.control_center.hide()

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
        if self.RETRIES >= 100:
            raise ConnectionRefusedError('Could not connect to any devices.')

        if self._client.address == '':
            scanner = BleakScanner()
            print('Scanning for bluetooth devices..')
            devices_found = await scanner.discover()
            print(f'{len(devices_found)} Bluetooth devices found.. looking for Puffco devices..')
            for device in devices_found:
                service_uuids = device.metadata.get('uuids')
                device_mac_address = device.address
                if device_mac_address in self._client.attempted_devices:
                    print(f'Ignoring {device.name} ({device_mac_address}), already failed to connect before')
                    continue

                if Characteristics.SERVICE_UUID in service_uuids or device.address.startswith('84:2E:14:'):
                    print(f'Potential Puffco Product "{device.name}" ({device.address})')
                    self._client.name = device.name
                    self._client.address = device.address
                    break

            if self._client.address == '':
                return await self.connect(retry=True)

        connected = False
        timeout = False
        try:
            connected = await self._client.connect(timeout=3, use_cached=not retry)
            await self._on_connect()
        except futures.TimeoutError:  # could not connect to device
            print('Timed out while connecting, retrying..')
            timeout = True
        except BleakError as e:  # could not find device
            print(f'(BLEAK) "{e}", retrying..')

        if self.home.ui_connectStatus.text() != 'DISCONNECTED' and not connected:
            self.home.ui_connectStatus.setText('DISCONNECTED')
            self.home.ui_connectStatus.setStyleSheet(f'color: red;')

        if connected:
            await self._client.pair()
        else:
            if retry:
                self.RETRIES += 1

            if not timeout:
                print('Failed to connect, retrying..')

            await sleep(2.5)  # reconnectDelayMs: 2500
            return await self.connect(retry=True)

        self.RETRIES = 0
        print('Connected!')
        return connected

    async def on_disconnect(self, client):
        await self.home.reset()
        if not self.isVisible():
            self.show()

        print(f'Lost connection to "{client.name}" ({client.address}), attempting to reconnect...')
        await self.connect(retry=True)

    async def _on_connect(self):
        self._client.set_disconnected_callback(lambda *args: ensure_future(self.on_disconnect(*args)))
        # Set the app theme (upon first launch):
        self.ctrl_center_btn.setDisabled(False)

        if settings.value('General/Theme', 'unset', str) == 'unset':
            model = await self._client.get_device_model()
            if model not in DEVICE_THEME_MAP:
                print(f'unknown device model {model}')
                builtins.theme = theme = DEVICE_THEME_MAP['0']  # basic/default
            else:
                builtins.theme = theme = DEVICE_THEME_MAP[model]

            settings.setValue('General/Theme', theme.name)
            if theme.name != 'basic':
                self.setStyleSheet(f"background-image: url({theme.BACKGROUND});\n"
                                   f"color: rgb{theme.TEXT_COLOR};\n"
                                   "border: 0px;")

                pixmap = self.ctrl_center_btn.alter_pixmap(self.ctrl_center_btn.path, size=(36, 36),
                                                           paint=True, color=QColor(*theme.TEXT_COLOR))
                self.ctrl_center_btn.setIconSize(pixmap.size())
                self.ctrl_center_btn.setIcon(QIcon(pixmap))

                self.home.device.device.setPixmap(QPixmap(theme.DEVICE))
                self.home.device.device.resize(291, 430)

                self.home.device.led.setMaximumWidth(self.home.device.device.width() - theme.LIGHTING_WIDTH_ADJ)
                self.home.device.led.setPixmap(QPixmap(theme.LIGHTING))
                self.home.device.led.resize(self.home.device.device.width() - theme.LIGHTING_WIDTH_ADJ, self.home.device.device.height())
                if self.home.device.color:
                    self.home.device.colorize(*self.home.device.color)

                for button in self.profiles.profile_buttons.values():
                    button._pixmap = QPixmap(theme.HOME_DATA)
                    button.update()

        # Activate control center buttons:
        for control in self.control_center.CONTROLS:
            value = settings.value(control.setting_name, False, bool)

            if 'lantern' in control.setting_name.lower():
                # send the lantern status and continue. we do not want to activate the button,
                # as that will cause the lantern UI to appear upon opening control center
                await self._client.send_lantern_status(True)
                continue

            if value:
                control.on_click()

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
            await self._client.change_profile(reset_idx, current=True)

        if self.profiles.isVisible():
            self.profiles.setVisible(False)

        await self.profiles.fill()
        await self.home.fill(from_callback=True)
        if not self.isVisible():
            self.show()

        self.profilesButton.setDisabled(False)
