from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFrame, QLabel

from .elements import Battery, DataLabel, DeviceVisualizer
from . import BleakError


class HomeScreen(QFrame):
    def __init__(self, parent):
        super(HomeScreen, self).__init__(parent)
        self.setMinimumSize(parent.width(), parent.height() - 130)
        self.move(0, 60)
        self.lower()
        self.setStyleSheet('background: transparent;')
        self.device = DeviceVisualizer(self)

        self.ui_deviceName = QLabel('- - - -', self)
        self.ui_deviceName.setMinimumWidth(parent.width() // 2)
        self.ui_deviceName.move(self.ui_deviceName.minimumWidth() // 2, 10)
        self.ui_deviceName.setAlignment(Qt.AlignCenter)
        self.ui_deviceName.setWordWrap(False)
        self.ui_deviceName.setStyleSheet('font-size: 30px;\n'
                                         'font-weight: bold;')
        self.ui_deviceName.adjustSize()

        self.statusLabel = QLabel('STATUS:', self)
        self.statusLabel.adjustSize()
        self.statusLabel.move((parent.width() // 3) + 10,
                              self.ui_deviceName.y() + self.ui_deviceName.height())

        self.statusLabel.setAlignment(Qt.AlignCenter)
        self.ui_connectStatus = QLabel('DISCONNECTED', self)
        self.ui_connectStatus.setMinimumHeight(self.statusLabel.height())
        self.ui_connectStatus.adjustSize()
        self.ui_connectStatus.move((parent.width() // 2) - 10, self.statusLabel.y())
        self.ui_connectStatus.setStyleSheet("color: red;")
        self.ui_connectStatus.setAlignment(Qt.AlignCenter)

        self.ui_battery = Battery(self)
        self.ui_battery.move(self.statusLabel.x() + 20, self.statusLabel.y() + self.statusLabel.height() + 5)

        self.ui_activeProfile = DataLabel(self, heading='ACTIVE PROFILE:', data='- -')
        self.ui_bowlTemp = DataLabel(self, heading='BOWL TEMPERATURE:', data='- -')
        self.ui_dailyDabCnt = DataLabel(self, heading='DAILY DABS:', data='- -')
        self.ui_totalDabCnt = DataLabel(self, heading='TOTAL DABS:', data='- -')

        self.ui_activeProfile.move(30, 175)
        self.ui_bowlTemp.move(30, 275)
        self.ui_dailyDabCnt.move(30, 375)
        self.ui_totalDabCnt.move(30, 475)
        if settings.value('Home/HideDabCounts', False, bool):
            self.ui_dailyDabCnt.hide()
            self.ui_totalDabCnt.hide()

        # bring the device visualization to the front of the layout
        self.device.raise_()

    async def reset(self):
        self.setUpdatesEnabled(False)
        self.ui_activeProfile.reset_properties()
        self.ui_bowlTemp.reset_properties()
        if not settings.value('Home/HideDabCounts', False, bool):
            self.ui_dailyDabCnt.reset_properties()
            self.ui_totalDabCnt.reset_properties()
        self.setUpdatesEnabled(True)

    async def fill(self, *, from_callback=False):
        self.setUpdatesEnabled(False)
        if from_callback:
            self.ui_connectStatus.setText('CONNECTED')
            self.ui_connectStatus.setStyleSheet('color: green;')
            self.ui_connectStatus.adjustSize()

        try:
            profile_name = await client.get_profile_name()
            if from_callback or (profile_name != self.ui_activeProfile.data):
                self.device.colorize(*await client.profile_color_as_rgb())
                self.ui_activeProfile.update_data(profile_name)

            await self.parent().update_battery()
            self.ui_bowlTemp.update_data(await client.get_bowl_temperature())
            if from_callback:
                self.ui_deviceName.setText(await client.get_device_name())
                self.ui_deviceName.adjustSize()
                if not settings.value('Home/HideDabCounts', False, bool):
                    self.ui_dailyDabCnt.update_data(await client.get_daily_dab_count())
                    self.ui_totalDabCnt.update_data(await client.get_total_dab_count())

        except BleakError:
            # no connection..
            pass

        if not self.isVisible():
            self.setVisible(True)

        self.setUpdatesEnabled(True)
