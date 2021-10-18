import bleak
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QFrame, QLabel, QPushButton, QWidget
from PyQt5.QtGui import QPixmap, QColor, QPainter

from asyncio import new_event_loop

HEADER_X = 30
HEADER_W = 200
HEADER_H = 20

HEADER_VALUE_SPACING = 40

VALUE_X = HEADER_X + 10
VALUE_W = 150
VALUE_H = 20


class HomeScreen(QFrame):
    DEFAULT_VALUES = {}

    def __init__(self, parent=None):
        super(HomeScreen, self).__init__(parent)
        self._client = getattr(parent, '_client')
        self.setStyleSheet('background: transparent;')

        d = QLabel('', self)
        d.setGeometry(HEADER_X - 10, 295, 280, 80) # x, y, w, h
        d.setStyleSheet('background: transparent;')
        #dd = QPixmap(':/assets/assets/home-data-gradient.png')
       # print('rect', dd.rect()) # rect PyQt5.QtCore.QRect(0, 0, 1095, 171)

        d.setPixmap(QPixmap(':/assets/assets/home-data-gradient.png'))

        self.preheatTestBtn = QPushButton('TEST', self)
        self.preheatTestBtn.setGeometry(310, 20, 113, 32)
        # self.preheatTestBtn.clicked.connect(lambda *args: asyncio.get_event_loop().run_until_complete(self.reset()))

        self.ui_deviceName = QLabel('----', self)
        self.ui_deviceName.setGeometry(HEADER_X, 110, HEADER_W, HEADER_H * 5)
        self.ui_deviceName.setAlignment(Qt.AlignCenter)
        self.ui_deviceName.setWordWrap(True)
        self.ui_deviceName.setStyleSheet('font-size: 36px;\n'
                                         'font-weight: bold;')
        self.ui_batteryPcnt = QLabel('- - %', self)
        self.ui_batteryPcnt.setGeometry(HEADER_X, 213, VALUE_W, VALUE_H)
        self.ui_batteryPcnt.setAlignment(Qt.AlignCenter)
        ########

        self.statusLabel = QLabel('STATUS:', self)
        self.statusLabel.setGeometry(HEADER_X - 15, 240, VALUE_W, VALUE_H)
        self.statusLabel.setAlignment(Qt.AlignCenter)
        connect_geometry = (self.statusLabel.width() + 5, self.statusLabel.y(), VALUE_W, VALUE_H)
        self.DEFAULT_VALUES['ui_connectStatus'] = {'geometry': connect_geometry}
        self.ui_connectStatus = QLabel('DISCONNECTED', self)
        self.ui_connectStatus.setGeometry(*connect_geometry)
        self.ui_connectStatus.setStyleSheet("color: rgb(255, 0, 0);")
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
        self.activeProfileLabel.setGeometry(HEADER_X, 300, HEADER_W, HEADER_H)
        self.activeProfileLabel.setAlignment(Qt.AlignCenter)
        self.ui_activeProfile = QLabel('- -', self)
        self.ui_activeProfile.setGeometry(VALUE_X, self.activeProfileLabel.y() + HEADER_VALUE_SPACING,
                                          VALUE_W, VALUE_H)
        self.ui_activeProfile.setAlignment(Qt.AlignCenter)

        self.label = QLabel("BOWL TEMPERATURE:", self)
        self.label.setGeometry(HEADER_X, self.ui_activeProfile.y() + (HEADER_VALUE_SPACING * 1.5),
                               HEADER_W, HEADER_H)
        self.label.setAlignment(Qt.AlignCenter)
        self.ui_bowlTemp = QLabel('- -', self)
        self.ui_bowlTemp.setGeometry(VALUE_X, self.label.y() + HEADER_VALUE_SPACING, VALUE_W, VALUE_H)
        self.ui_bowlTemp.setAlignment(Qt.AlignCenter)

        self.dailyDabLabel = QLabel('DAILY DABS:', self)
        self.dailyDabLabel.setGeometry(HEADER_X, self.ui_bowlTemp.y() + (HEADER_VALUE_SPACING * 1.5),
                                       HEADER_W, HEADER_H)
        self.dailyDabLabel.setAlignment(Qt.AlignCenter)
        self.ui_dailyDabCnt = QLabel('- -', self)
        self.ui_dailyDabCnt.setGeometry(VALUE_X, self.dailyDabLabel.y() + HEADER_VALUE_SPACING, VALUE_W, VALUE_H)
        self.ui_dailyDabCnt.setAlignment(Qt.AlignCenter)

        self.totalDabLabel = QLabel('TOTAL DABS:', self)
        self.totalDabLabel.setGeometry(HEADER_X, self.ui_dailyDabCnt.y() + (HEADER_VALUE_SPACING * 1.5),
                                       HEADER_W, HEADER_H)
        self.totalDabLabel.setAlignment(Qt.AlignCenter)
        self.ui_totalDabCnt = QLabel('- -', self)
        self.ui_totalDabCnt.setGeometry(VALUE_X, self.totalDabLabel.y() + HEADER_VALUE_SPACING, VALUE_W, VALUE_H)
        self.ui_totalDabCnt.setAlignment(Qt.AlignCenter)
        self.temperature_timer = QTimer(self)
        self.temperature_timer.setInterval(1000 * 3)
        self.temperature_timer.timeout.connect(lambda: new_event_loop().run_until_complete(self.update_loop()))
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

            geometry = attributes.get('geometry', None)
            if geometry:
                obj.setGeometry(*geometry)

        self.setUpdatesEnabled(True)

    async def fill(self, *, from_callback=False):
        self.setUpdatesEnabled(False)
        print('connected', self._client.is_connected)
        print(await self._client.get_operating_state())
        if from_callback:
            self.ui_connectStatus.setText('CONNECTED')
            self.ui_connectStatus.setStyleSheet('color: green;')
            self.ui_deviceName.setText(await self._client.get_device_name())

        profile_name = await self._client.get_profile_name()
        if from_callback or (profile_name != self.ui_activeProfile.text()):
            await self.colorize_led_overlay()
            self.ui_activeProfile.setText(profile_name)

        self.ui_bowlTemp.setText(await self._client.get_bowl_temperature())
        self.ui_dailyDabCnt.setText(await self._client.get_daily_dab_count())
        self.ui_totalDabCnt.setText(await self._client.get_total_dab_count())
        self.ui_batteryPcnt.setText(await self._client.get_battery_percentage())
        if not self.isVisible():
            self.setVisible(True)

        self.setUpdatesEnabled(True)

    async def colorize_led_overlay(self):
        r, g, b = await self._client.profile_colour_as_rgb()

        pixmap = QPixmap(":/assets/peakLED.png")
        painter = QPainter(pixmap)
        painter.setCompositionMode(painter.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(), QColor(r, g, b))
        painter.end()
        self.peakDeviceLED.setPixmap(pixmap)
        self.peakDeviceLED.update()

    async def update_loop(self):
        """ Update the elements on this frame (if shown) """
        if (not self.isVisible()) or (not self._client.is_connected):
            return

        print('update loop')
        temp = await self._client.get_bowl_temperature()
        if self.ui_bowlTemp.text() != temp:
            self.ui_bowlTemp.setText(temp)

        #await self.fill()
