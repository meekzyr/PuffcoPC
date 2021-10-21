from asyncio import ensure_future

import bleak
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QFrame, QLabel

from .elements import Battery, DataLabel, DeviceVisualizer


class HomeScreen(QFrame):
    def __init__(self, parent):
        super(HomeScreen, self).__init__(parent)
        self.setStyleSheet('background: transparent;')
        self.device = DeviceVisualizer(self)

        self.ui_deviceName = QLabel('- - - -', self)
        self.ui_deviceName.setMinimumWidth(parent.width() // 2)
        self.ui_deviceName.move(self.ui_deviceName.minimumWidth() // 2, 90)
        self.ui_deviceName.setAlignment(Qt.AlignCenter)
        self.ui_deviceName.setWordWrap(False)
        self.ui_deviceName.setStyleSheet('font-size: 36px;\n'
                                         'font-weight: bold;')
        self.ui_deviceName.adjustSize()

        ########

        self.statusLabel = QLabel('STATUS:', self)
        self.statusLabel.adjustSize()
        self.statusLabel.move((parent.width() // 3) + 10,
                              self.ui_deviceName.y() + self.ui_deviceName.height() + 5)

        self.statusLabel.setAlignment(Qt.AlignCenter)
        self.ui_connectStatus = QLabel('DISCONNECTED', self)
        self.ui_connectStatus.setMinimumHeight(self.statusLabel.height())
        self.ui_connectStatus.adjustSize()
        self.ui_connectStatus.move((parent.width() // 2) - 10, self.statusLabel.y())
        self.ui_connectStatus.setStyleSheet("color: red;")
        self.ui_connectStatus.setAlignment(Qt.AlignCenter)

        self.ui_battery = Battery(self)
        self.ui_battery.move(self.statusLabel.x() + 30, self.statusLabel.y() + self.statusLabel.height() + 5)

        self.ui_activeProfile = DataLabel(self, heading='ACTIVE PROFILE:', data='- -')
        self.ui_bowlTemp = DataLabel(self, heading='BOWL TEMPERATURE:', data='- -')
        self.ui_dailyDabCnt = DataLabel(self, heading='DAILY DABS:', data='- -')
        self.ui_totalDabCnt = DataLabel(self, heading='TOTAL DABS:', data='- -')

        self.ui_activeProfile.move(20, 300)
        self.ui_bowlTemp.move(20, 400)
        self.ui_dailyDabCnt.move(20, 500)
        self.ui_totalDabCnt.move(20, 600)

        # bring the device visualization to the front of the layout
        self.device.raise_()

        self.temperature_timer = QTimer(self)
        self.temperature_timer.setInterval(1000 * 3)  # 3s
        self.temperature_timer.timeout.connect(lambda: ensure_future(self.update_loop()).done())
        self.temperature_timer.start()

    async def reset(self):
        self.setUpdatesEnabled(False)
        self.ui_activeProfile.reset_properties()
        self.ui_bowlTemp.reset_properties()
        self.ui_dailyDabCnt.reset_properties()
        self.ui_totalDabCnt.reset_properties()
        self.setUpdatesEnabled(True)

    async def fill(self, *, from_callback=False):
        self.setUpdatesEnabled(False)
        if from_callback:
            self.ui_connectStatus.setText('CONNECTED')
            self.ui_connectStatus.setStyleSheet('color: green;')
            self.ui_connectStatus.adjustSize()
            self.ui_deviceName.setText(await client.get_device_name())
            self.ui_deviceName.adjustSize()

        try:
            profile_name = await client.get_profile_name()
            if from_callback or (profile_name != self.ui_activeProfile.data):
                self.device.colorize(*await client.profile_color_as_rgb())
                self.ui_activeProfile.update_data(profile_name)

            self.ui_bowlTemp.update_data(await client.get_bowl_temperature())
            self.ui_dailyDabCnt.update_data(await client.get_daily_dab_count())
            self.ui_totalDabCnt.update_data(await client.get_total_dab_count())

            percentage = await client.get_battery_percentage()
            is_charging = await client.currently_charging
            eta = None
            if is_charging:
                eta = await client.get_battery_charge_eta()
                hr, rem = divmod(eta, 3600)
                mins, sec = divmod(rem, 60)
                eta = f'{str(int(mins)).zfill(2)}:{str(int(sec)).zfill(2)}'
                if hr > 0:
                    eta = str(int(hr)).zfill(2) + eta

            self.ui_battery.update_battery(percentage, is_charging, eta)
        except bleak.BleakError:
            # no connection..
            pass

        if not self.isVisible():
            self.setVisible(True)

        self.setUpdatesEnabled(True)

    async def update_loop(self):
        """ Update the elements on this frame (if shown) """
        if (not self.isVisible()) or (not client.is_connected):
            return

        # todo: only constantly check for bowl temp and profile/led updates in this loop
        #  use operating state and/or profile times to determine when to query for updates
        try:
            #print(await client.get_battery_charge_eta())
            await client.change_profile(await client.get_profile())  # needed to get profile name

            profile_name = await client.get_profile_name()
            temp = await client.get_bowl_temperature()

            total = await client.get_total_dab_count()
            if self.ui_totalDabCnt.data != total:  # check if our dab count has changed
                self.ui_totalDabCnt.update_data(total)
                # we can update the daily avg as well
                self.ui_dailyDabCnt.update_data(await client.get_daily_dab_count())

            if profile_name and self.ui_activeProfile.data != profile_name:
                self.ui_activeProfile.update_data(profile_name)
                self.device.colorize(*await client.profile_color_as_rgb())

            if temp and self.ui_bowlTemp.data != temp:
                self.ui_bowlTemp.update_data(temp)

        #await self.fill()

        except bleak.BleakError:
            # device is not connected, or our characteristics have not
            # been populated
            return
