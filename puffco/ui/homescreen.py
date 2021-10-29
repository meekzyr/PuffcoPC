from asyncio import ensure_future

import bleak
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QFrame, QLabel

from .elements import Battery, DataLabel, DeviceVisualizer
from puffco.btnet import OperatingState


class HomeScreen(QFrame):
    last_charging_state = None
    current_operating_state = None
    current_profile_id = None

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

        self.op_timer = QTimer(self)
        self.op_timer.setInterval(1000 * 2)  # 2s
        self.op_timer.timeout.connect(lambda: ensure_future(self.update_loop()).done())
        self.op_timer.start()

        self.temp_timer = QTimer(self)
        self.temp_timer.setInterval(1000)  # 1s
        self.temp_timer.timeout.connect(lambda: ensure_future(self.update_temp()).done())

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

            await self.update_battery()
            self.ui_bowlTemp.update_data(await client.get_bowl_temperature())
            if from_callback:
                self.ui_deviceName.setText(await client.get_device_name())
                self.ui_deviceName.adjustSize()
                if not settings.value('Home/HideDabCounts', False, bool):
                    self.ui_dailyDabCnt.update_data(await client.get_daily_dab_count())
                    self.ui_totalDabCnt.update_data(await client.get_total_dab_count())

        except bleak.BleakError:
            # no connection..
            pass

        if not self.isVisible():
            self.setVisible(True)

        self.setUpdatesEnabled(True)

    async def update_battery(self):
        if not client.is_connected:
            return

        try:
            percentage = await client.get_battery_percentage()
            is_charging = await client.currently_charging
            eta = None
            if is_charging:
                eta = await client.get_battery_charge_eta()
                hr, rem = divmod(eta, 3600)
                mins, sec = divmod(rem, 60)
                eta = f'{str(int(mins)).zfill(2)}:{str(int(sec)).zfill(2)}'
                if hr > 0:
                    eta = str(int(hr)).zfill(2) + f':{eta}'

            self.ui_battery.update_battery(percentage, is_charging, eta)
        except bleak.BleakError:
            pass

    async def update_temp(self):
        if not client.is_connected:
            return

        try:
            temp = await client.get_bowl_temperature()
            num = ''.join(filter(str.isdigit, temp))
            if not num:
                # atomizer is disconnected, check for changes every 20s
                self.temp_timer.setInterval(1000 * 20)
            elif int(num) <= 100:
                #  we are at/below 100 Fahrenheit.. stop our ival
                self.temp_timer.stop()

            active_prof_window = self.parent().profiles.active_profile
            if not active_prof_window:
                profile_id = await client.get_profile()
                self.parent().profiles.select_profile(profile_id)
                active_prof_window = self.parent().profiles.active_profile
                active_prof_window.verified = True

            if active_prof_window:
                if not active_prof_window.verified:
                    profile_id = await client.get_profile()
                    if profile_id != active_prof_window.idx:
                        self.parent().profiles.select_profile(profile_id)
                        active_prof_window = self.parent().profiles.active_profile

                    active_prof_window.verified = True

                if self.current_operating_state in (OperatingState.PREHEATING, OperatingState.HEATED) and \
                        not active_prof_window.started:
                    # adjust the UI if we have not already done so
                    active_prof_window.start(send_command=False)

                active_prof_window.update_temp_reading(temp)

            if temp and self.ui_bowlTemp.data != temp:
                self.ui_bowlTemp.update_data(temp)

        except bleak.BleakError:
            pass

    async def update_loop(self):
        """ Update the elements on this frame (if shown) """
        if not client.is_connected:
            return

        try:
            led = self.device.led
            if settings.value('Modes/Stealth', False, bool):
                if not led.isHidden():
                    led.hide()
            else:
                if led.isHidden():
                    led.show()

            operating_state = await client.get_operating_state()
            if settings.value('Modes/Ready', False, bool) and operating_state not in \
                    (OperatingState.PREHEATING, OperatingState.HEATED):
                is_charging = await client.currently_charging
                if self.last_charging_state is True and self.last_charging_state != is_charging:
                    await client.preheat()

                self.last_charging_state = is_charging

            if self.current_operating_state != operating_state:
                # Handle operating state changes:
                if self.current_operating_state:
                    # todo: handle changes
                    print(f'operating state changed {OperatingState(self.current_operating_state).name} --> {OperatingState(operating_state).name}')
                    if self.current_operating_state in (OperatingState.PREHEATING, OperatingState.HEATED):
                        # we just came out of a heat cycle
                        await self.update_battery()

                        # slow our temp reader, and make sure it is started/active
                        # it will automatically stop once it hits 100*F
                        self.temp_timer.setInterval(1000 * 3)
                        if not self.temp_timer.isActive():
                            self.temp_timer.start()

                        # lets update the dab count
                        if not settings.value('Home/HideDabCounts', False, bool):
                            total = await client.get_total_dab_count()
                            if self.ui_totalDabCnt.data != total:  # check if our dab count has changed
                                self.ui_totalDabCnt.update_data(total)
                                # we can update the daily avg as well
                                self.ui_dailyDabCnt.update_data(await client.get_daily_dab_count())

                        if operating_state not in (OperatingState.PREHEATING, OperatingState.HEATED):
                            active_prof_window = self.parent().profiles.active_profile
                            if active_prof_window and active_prof_window.started:
                                active_prof_window.cycle_finished()

                self.current_operating_state = operating_state

            # Current operating state handling:
            if operating_state == OperatingState.ON_TEMP_SELECT:
                current_profile_id = await client.get_profile()
                if self.current_profile_id != current_profile_id:
                    await client.change_profile(current_profile_id)
                    if self.current_profile_id:
                        profile_name = await client.get_profile_name()
                        if profile_name and self.ui_activeProfile.data != profile_name:
                            self.ui_activeProfile.update_data(profile_name)
                            self.device.colorize(*await client.profile_color_as_rgb())

                    self.current_profile_id = current_profile_id

            elif operating_state in (OperatingState.PREHEATING, OperatingState.HEATED):
                self.temp_timer.setInterval(1000)
                if not self.temp_timer.isActive():
                    self.temp_timer.start()

            elif operating_state == OperatingState.COOLDOWN:
                # we are fresh out of a heat cycle, lets update the battery display and slow our temperature updates
                self.temp_timer.setInterval(1000 * 3)
                await self.update_battery()

        except bleak.BleakError:
            # device is not connected, or our characteristics have not been populated
            pass
