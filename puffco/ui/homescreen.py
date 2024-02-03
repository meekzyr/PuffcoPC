from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QLabel

from . import BleakError
from .elements import Battery, DataLabel, DeviceVisualizer


class HomeScreen(QFrame):
    def __init__(self, parent):
        super(HomeScreen, self).__init__(parent)
        self.setMinimumSize(parent.width(), parent.height() - 130)
        self.move(0, 60)
        self.lower()
        self.setStyleSheet('background: transparent;')
        self.device = DeviceVisualizer(self)

        self.ui_device_name = QLabel('- - - -', self)
        self.ui_device_name.setMinimumWidth(parent.width() // 2)
        self.ui_device_name.move(self.ui_device_name.minimumWidth() // 2, 10)
        self.ui_device_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ui_device_name.setWordWrap(False)
        self.ui_device_name.setStyleSheet('font-size: 30px;\n'
                                          'font-weight: bold;')
        self.ui_device_name.adjustSize()

        self.status_label = QLabel('STATUS:', self)
        self.status_label.adjustSize()
        self.status_label.move((parent.width() // 3) + 10,
                               self.ui_device_name.y() + self.ui_device_name.height())

        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ui_connect_status = QLabel('DISCONNECTED', self)
        self.ui_connect_status.setMinimumHeight(self.status_label.height())
        self.ui_connect_status.adjustSize()
        self.ui_connect_status.move((parent.width() // 2) - 10, self.status_label.y())
        self.ui_connect_status.setStyleSheet("color: red;")
        self.ui_connect_status.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.ui_battery = Battery(self)
        self.ui_battery.move(self.status_label.x() + 20, self.status_label.y() + self.status_label.height() + 5)

        self.ui_active_profile = DataLabel(self, heading='ACTIVE PROFILE:', data='- -')
        self.ui_bowl_temp = DataLabel(self, heading='BOWL TEMPERATURE:', data='- -')
        self.ui_daily_dab_cnt = DataLabel(self, heading='DAILY DABS:', data='- -')
        self.ui_total_dab_cnt = DataLabel(self, heading='TOTAL DABS:', data='- -')

        self.ui_active_profile.move(30, 175)
        self.ui_bowl_temp.move(30, 275)
        self.ui_daily_dab_cnt.move(30, 375)
        self.ui_total_dab_cnt.move(30, 475)
        if settings.value('Home/HideDabCounts', False, bool):
            self.ui_daily_dab_cnt.hide()
            self.ui_total_dab_cnt.hide()

        # bring the device visualization to the front of the layout
        self.device.raise_()

    async def reset(self):
        self.setUpdatesEnabled(False)
        self.ui_active_profile.reset_properties()
        self.ui_bowl_temp.reset_properties()
        if not settings.value('Home/HideDabCounts', False, bool):
            self.ui_daily_dab_cnt.reset_properties()
            self.ui_total_dab_cnt.reset_properties()
        self.setUpdatesEnabled(True)

    def update_connection_status(self, text, text_color: str = None):
        self.ui_connect_status.setText(text)
        if text_color:
            self.ui_connect_status.setStyleSheet(f'color: {text_color}')
        self.ui_connect_status.adjustSize()

    async def fill(self, *, from_callback=False):
        self.setUpdatesEnabled(False)
        if from_callback:
            self.update_connection_status('CONNECTED', '#4CD964')

        try:
            profile_name = await client.get_profile_name()
            if from_callback or (profile_name != self.ui_active_profile.data):
                self.device.colorize(*await client.profile_color_as_rgb())
                self.ui_active_profile.update_data(profile_name)

            await self.parent().update_battery()
            self.ui_bowl_temp.update_data(await client.get_bowl_temperature())
            if from_callback:
                self.ui_device_name.setText(await client.get_device_name())
                self.ui_device_name.adjustSize()
                if not settings.value('Home/HideDabCounts', False, bool):
                    self.ui_daily_dab_cnt.update_data(await client.get_daily_dab_count())
                    self.ui_total_dab_cnt.update_data(await client.get_total_dab_count())

        except BleakError:
            # no connection..
            pass

        if not self.isVisible():
            self.setVisible(True)

        self.setUpdatesEnabled(True)
