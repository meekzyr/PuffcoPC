import asyncio

import bleak
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QFrame, QLabel, QWidget
from PyQt5.QtGui import QPixmap, QColor, QPainter

HEADER_X = 30
HEADER_W = 200
HEADER_H = 20

HEADER_VALUE_SPACING = 40

VALUE_X = HEADER_X + 10
VALUE_W = 150
VALUE_H = 20


class HomeScreen(QFrame):
    DEFAULT_VALUES = {}

    def __init__(self, parent):
        super(HomeScreen, self).__init__(parent)
        self.setStyleSheet('background: transparent;')

        # TODO: BigShouldersDisplay-Medium font (:/fonts/bigshoulders-medium.ttf)
        d = QLabel('', self)
        d.setGeometry(HEADER_X - 10, 295, 280, 80)  # x, y, w, h
        d.setStyleSheet('background: transparent;')
        d.setPixmap(QPixmap(':/assets/data-gradient.png'))

        self.ui_deviceName = QLabel('----', self)
        self.ui_deviceName.move(HEADER_X, 110)
        self.ui_deviceName.adjustSize()
        self.ui_deviceName.setAlignment(Qt.AlignCenter)
        self.ui_deviceName.setWordWrap(True)
        self.ui_deviceName.setStyleSheet('font-size: 36px;\n'
                                         'font-weight: bold;')
        self.ui_batteryPcnt = QLabel('- - %', self)
        self.ui_batteryPcnt.move(HEADER_X, 213)
        self.ui_batteryPcnt.adjustSize()
        self.ui_batteryPcnt.setAlignment(Qt.AlignCenter)
        ########

        self.statusLabel = QLabel('STATUS:', self)
        self.statusLabel.move(HEADER_X - 15, 240)
        self.statusLabel.adjustSize()
        self.statusLabel.setAlignment(Qt.AlignCenter)
        self.ui_connectStatus = QLabel('DISCONNECTED', self)
        self.ui_connectStatus.move(self.statusLabel.width() + 20, self.statusLabel.y())
        self.ui_connectStatus.adjustSize()
        self.ui_connectStatus.setStyleSheet("color: red;")
        self.ui_connectStatus.setAlignment(Qt.AlignCenter)

        self.peakDeviceImg = QLabel('', self)
        self.peakDeviceImg.setGeometry(210, 190, 291, 511)
        self.peakDeviceImg.setPixmap(QPixmap(":/assets/peak.png"))
        self.peakDeviceImg.setScaledContents(True)
        self.peakDeviceImg.setAlignment(Qt.AlignCenter)
        led_geometry = list(self.peakDeviceImg.geometry().getRect())
        led_geometry[2] -= 50  # resize the overlay to fit properly
        self.peakDeviceLED = QLabel('', self)
        self.peakDeviceLED.setGeometry(*led_geometry)
        self.peakDeviceLED.setPixmap(QPixmap(":/assets/peakLED.png"))
        self.peakDeviceLED.setScaledContents(True)
        self.peakDeviceLED.setAlignment(Qt.AlignCenter)
        self.peakDeviceLED.setStyleSheet(None)

        self.activeProfileLabel = QLabel('ACTIVE PROFILE:', self)
        self.activeProfileLabel.move(HEADER_X, 300)
        self.activeProfileLabel.adjustSize()
        self.activeProfileLabel.setAlignment(Qt.AlignCenter)
        self.ui_activeProfile = QLabel('- -', self)
        self.ui_activeProfile.move(VALUE_X, self.activeProfileLabel.y() + HEADER_VALUE_SPACING)
        self.ui_activeProfile.adjustSize()
        self.ui_activeProfile.setAlignment(Qt.AlignCenter)

        self.label = QLabel("BOWL TEMPERATURE:", self)
        self.label.move(HEADER_X, self.ui_activeProfile.y() + (HEADER_VALUE_SPACING * 1.5))
        self.label.adjustSize()
        self.label.setAlignment(Qt.AlignCenter)
        self.ui_bowlTemp = QLabel('- -', self)
        self.ui_bowlTemp.move(VALUE_X, self.label.y() + HEADER_VALUE_SPACING)
        self.ui_bowlTemp.adjustSize()
        self.ui_bowlTemp.setAlignment(Qt.AlignCenter)

        self.dailyDabLabel = QLabel('DAILY DABS:', self)
        self.dailyDabLabel.move(HEADER_X, self.ui_bowlTemp.y() + (HEADER_VALUE_SPACING * 1.5))
        self.dailyDabLabel.adjustSize()
        self.dailyDabLabel.setAlignment(Qt.AlignCenter)
        self.ui_dailyDabCnt = QLabel('- -', self)
        self.ui_dailyDabCnt.move(VALUE_X, self.dailyDabLabel.y() + HEADER_VALUE_SPACING)
        self.ui_dailyDabCnt.adjustSize()
        self.ui_dailyDabCnt.setAlignment(Qt.AlignCenter)

        self.totalDabLabel = QLabel('TOTAL DABS:', self)
        self.totalDabLabel.move(HEADER_X, self.ui_dailyDabCnt.y() + (HEADER_VALUE_SPACING * 1.5))
        self.totalDabLabel.adjustSize()
        self.totalDabLabel.setAlignment(Qt.AlignCenter)
        self.ui_totalDabCnt = QLabel('- -', self)
        self.ui_totalDabCnt.move(VALUE_X, self.totalDabLabel.y() + HEADER_VALUE_SPACING)
        self.ui_totalDabCnt.adjustSize()
        self.ui_totalDabCnt.setAlignment(Qt.AlignCenter)
        self.temperature_timer = QTimer(self)
        self.temperature_timer.setInterval(1000 * 3)  # 3s
        self.temperature_timer.timeout.connect(lambda: asyncio.ensure_future(self.update_loop()).done())
        self.temperature_timer.start()

        for variable, obj in self.widgets:
            self.DEFAULT_VALUES.setdefault(variable, {})
            obj_specific_stylesheet = getattr(obj, 'styleSheet', lambda: '')()
            obj_text = getattr(obj, 'text', lambda: '')()
            if obj_specific_stylesheet:
                self.DEFAULT_VALUES[variable]['stylesheet'] = obj_specific_stylesheet
            if obj_text:
                self.DEFAULT_VALUES[variable]['text'] = obj_text

    @property
    def widgets(self):
        return [(k, v) for (k, v) in self.__dict__.items() if issubclass(v.__class__, QWidget)]

    async def reset(self):
        self.setUpdatesEnabled(False)
        for var, attributes in self.DEFAULT_VALUES.items():
            obj = getattr(self, var, None)
            if obj is None:
                continue

            text = attributes.get('text', None)
            if text is not None and obj.text() != text:
                obj.setText(text)

            stylesheet = attributes.get('stylesheet', None)
            if stylesheet is not None and obj.styleSheet() != stylesheet:
                obj.setStyleSheet(stylesheet)

        self.setUpdatesEnabled(True)

    async def fill(self, *, from_callback=False):
        self.setUpdatesEnabled(False)
        if from_callback:
            self.ui_connectStatus.setText('CONNECTED')
            self.ui_connectStatus.setStyleSheet('color: green;')
            self.ui_connectStatus.adjustSize()
            self.ui_deviceName.setText(await client.get_device_name())
            self.ui_deviceName.adjustSize()

        profile_name = await client.get_profile_name()
        if from_callback or (profile_name != self.ui_activeProfile.text()):
            await self.colorize_led_overlay()
            self.ui_activeProfile.setText(profile_name)
            self.ui_activeProfile.adjustSize()

        self.ui_bowlTemp.setText(await client.get_bowl_temperature())
        self.ui_bowlTemp.adjustSize()
        self.ui_dailyDabCnt.setText(await client.get_daily_dab_count())
        self.ui_dailyDabCnt.adjustSize()
        self.ui_totalDabCnt.setText(await client.get_total_dab_count())
        self.ui_totalDabCnt.adjustSize()
        self.ui_batteryPcnt.setText(await client.get_battery_percentage())
        self.ui_batteryPcnt.adjustSize()

        if not self.isVisible():
            self.setVisible(True)

        self.setUpdatesEnabled(True)

    async def colorize_led_overlay(self, profile_id: int = None):
        r, g, b = await client.profile_color_as_rgb(profile_id)

        pixmap = QPixmap(":/assets/peakLED.png")
        painter = QPainter(pixmap)
        painter.setCompositionMode(painter.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(), QColor(r, g, b))
        painter.end()
        self.peakDeviceLED.setPixmap(pixmap)
        self.peakDeviceLED.update()

    async def update_loop(self):
        """ Update the elements on this frame (if shown) """
        if (not self.isVisible()) or (not client.is_connected):
            return

        try:
            await client.change_profile(await client.get_profile())  # needed to get profile name

            profile_name = await client.get_profile_name()
            temp = await client.get_bowl_temperature()

            total = await client.get_total_dab_count()
            if self.ui_totalDabCnt.text() != total:  # check if our dab count has changed
                self.ui_totalDabCnt.setText(total)
                # we can update the daily avg as well
                self.ui_dailyDabCnt.setText(await client.get_daily_dab_count())

        except bleak.BleakError:
            # device is not connected, or our characteristics have not
            # been populated
            return

        if profile_name and self.ui_activeProfile.text() != profile_name:
            self.ui_activeProfile.setText(profile_name)
            self.ui_activeProfile.adjustSize()
            await self.colorize_led_overlay()

        if temp and self.ui_bowlTemp.text() != temp:
            self.ui_bowlTemp.setText(temp)
            self.ui_bowlTemp.adjustSize()

        #await self.fill()
