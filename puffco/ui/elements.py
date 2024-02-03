from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPainter, QColor, QPixmap, QFont, QIcon
from PyQt6.QtWidgets import QAbstractButton, QLabel, QGraphicsBlurEffect, QFrame, QPushButton


class DeviceVisualizer(QFrame):
    def __init__(self, parent):
        super(DeviceVisualizer, self).__init__(parent)
        self.move(215, 150)
        self.setStyleSheet('background: transparent;')
        self.device = QLabel('', self)
        self.device.setPixmap(QPixmap(theme.DEVICE))
        self.device.resize(291, 430)
        self.device.setScaledContents(True)
        self.led = QLabel('', self)
        self.led.setFixedHeight(self.device.height())
        self.led.setMaximumWidth(self.device.width() - theme.LIGHTING_WIDTH_ADJ)

        self.led.setPixmap(QPixmap(theme.LIGHTING))
        self.led.setScaledContents(True)
        self.led.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.led.setStyleSheet(None)
        self.color = None

    def colorize(self, r: int, g: int, b: int, alpha: int = 255):
        self.color = (r, g, b)
        pixmap = QPixmap(theme.LIGHTING)
        painter = QPainter(pixmap)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(), QColor(r, g, b, alpha))
        painter.end()
        self.led.setPixmap(pixmap)
        b = QGraphicsBlurEffect()
        b.setBlurRadius(5)
        b.setBlurHints(QGraphicsBlurEffect.BlurHint.QualityHint)
        self.led.setGraphicsEffect(b)
        self.led.raise_()
        self.led.update()


class ImageButton(QPushButton):
    PIXMAP = None

    def __init__(self, asset_path, parent, callback=None, *, size=None, color=None, paint=True):
        super(ImageButton, self).__init__('', parent)
        self.path = asset_path
        pixmap = self.alter_pixmap(asset_path, size, paint, color)
        self._p = pixmap
        self.setIconSize(pixmap.size())
        self.setIcon(QIcon(pixmap))
        self.setStyleSheet('background: transparent;')
        self.adjustSize()

        if callback:
            self.clicked.connect(callback)

    def alter_pixmap(self, asset_path, size, paint, color):
        pixmap = QPixmap(asset_path)
        if size:
            if isinstance(size, QSize):
                w, h = size.width(), size.height()
            else:
                w, h = size
            if w > pixmap.width():
                w = pixmap.width()
            if h > pixmap.height():
                h = pixmap.height()
            pixmap = pixmap.scaled(w, h)

        if paint:
            painter = QPainter(pixmap)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
            painter.fillRect(pixmap.rect(), color or QColor(255, 255, 255))
            painter.end()

        self.PIXMAP = pixmap
        return pixmap

    def resize(self, w: int, h: int) -> None:
        self.setIconSize(QSize(w, h))
        return super(ImageButton, self).resize(w, h)


class ProfileButton(QAbstractButton):
    def __init__(self, parent, i, geom, *, callback):
        super(ProfileButton, self).__init__(parent)
        self.home = parent.parent()
        self._idx = i
        self.setObjectName(f'ProfileButton-{i}')
        self.setGeometry(*geom)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.pix_asset = theme.HOME_DATA
        self._pixmap = QPixmap(self.pix_asset)

        # add a 2px grayish border around us
        self._border = QFrame(parent)
        self._border.setGeometry(self.geometry())
        self._border.move(self.pos())
        self._border.setStyleSheet('border: 2px #191919;'
                                   'border-style: outset;')

        self.duration = QLabel('', self)
        self.duration.setFont(QFont('Slick', 11))
        self.duration.move(350, 80)
        self.duration.adjustSize()

        f = QFont(self.font().family(), 16)
        f.setStretch(QFont.Stretch.Unstretched * 1.5)

        self.profile_name = QLabel('', self)
        self.profile_name.setFont(f)
        self.profile_name.move(10, 5)
        self.temperature = QLabel('', self)
        f.setStretch(QFont.Stretch.Unstretched)
        f.setPointSize(32)
        f.setBold(True)
        self.temperature.setFont(f)
        self.temperature.move(10, 50)

        self.glow = QLabel('', self)
        self.glow.setPixmap(QPixmap(':/themes/profile_bg_glow.png'))
        self.glow.move(150, -30)
        b = QGraphicsBlurEffect()
        b.setBlurRadius(5)
        self.glow.setGraphicsEffect(b)
        self.glow.adjustSize()
        self.color = None
        self.clicked.connect(lambda: callback(i))

    def pixmap(self):
        return self._pixmap

    def set_pixmap_color(self, color):
        self.color = color
        # color our glow effect
        pm = self.glow.pixmap()
        painter = QPainter(pm)
        painter.setOpacity(0.9)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(pm.rect(), QColor(*color))
        painter.end()
        self.update()

    def set_profile_name(self, name):
        self.profile_name.setText(name)
        self.profile_name.adjustSize()

    def set_duration(self, duration):
        self.duration.setText(str(duration))
        self.duration.adjustSize()

    def set_temperature(self, temperature):
        self.temperature.setText(temperature)
        self.temperature.adjustSize()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setOpacity(0.9)
        mode = QPainter.CompositionMode.CompositionMode_Overlay
        if self.home.PROFILES[self._idx].rainbow:
            if settings.value('General/Theme', 'unset', str) != 'opal':
                mode = QPainter.CompositionMode.CompositionMode_Lighten
            else:
                mode = QPainter.CompositionMode.CompositionMode_SourceIn

        if self.color:
            painter.fillRect(event.rect(), QColor(*self.color))
        painter.setCompositionMode(mode)
        painter.drawPixmap(event.rect(), self._pixmap)
        painter.end()

    def sizeHint(self):
        return self._pixmap.size()


class DataLabel(QLabel):
    default_heading = 'Heading'
    default_data = 'Data'

    def __init__(self, parent, *, heading='Heading', data='- -'):
        self.default_heading = heading
        self.default_data = data

        super(DataLabel, self).__init__('', parent)
        self.setStyleSheet('background: transparent;')
        self.setPixmap(QPixmap(theme.HOME_DATA))
        self.setScaledContents(True)
        self.setMaximumSize(340, 80)
        self.setMinimumSize(280, 80)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.heading = QLabel(heading, self)
        self.heading.move(10, 5)
        self.heading.adjustSize()
        self.heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._data = QLabel(data, self)
        self._data.move(15, 45)
        self._data.adjustSize()
        self._data.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def update_data(self, data: str):
        self._data.setText(data)
        self._data.adjustSize()

    def reset_properties(self):
        if self.heading.text() != self.default_heading:
            self.heading.setText(self.default_heading)
            self.heading.adjustSize()

        if self._data.text() != self.default_data:
            self._data.setText(self.default_data)
            self._data.adjustSize()

    @property
    def data(self) -> str:
        return self._data.text()


class Battery(QFrame):
    _asset: str = ':/battery/unknown.png'

    def __init__(self, parent):
        super(Battery, self).__init__(parent)
        self.setStyleSheet('background: transparent;')
        self.current_percentage = None
        self.last_charge_state = False
        self.percent = QLabel('--- %', self)
        self.percent.move(10, 0)
        self.percent.adjustSize()
        self.icon = QLabel('', self)
        self.icon.setMinimumSize(64, 21)
        self.icon.setPixmap(QPixmap(self._asset).scaled(41, 21))
        self.icon.move(55, 3)
        self.eta = QLabel('', self)
        shrink = self.eta.font()
        shrink.setPointSize(12)
        self.eta.setFont(shrink)
        self.eta.move(0, (self.percent.y() + self.percent.height()) + 3)
        self.eta.setMinimumWidth(200)
        self.eta.setScaledContents(True)

    def update_battery(self, percent: int, charging: bool, eta: str = None):
        if self.icon.x() != 50:
            self.icon.move(50, self.icon.y())

        if self.eta.isHidden():
            self.eta.show()

        if eta:
            self.eta.setText(f'Charge ETA: ~ {eta}')
            self.eta.adjustSize()
        elif self.eta.text() and eta is None:
            self.eta.setText('')
            self.eta.adjustSize()

        if percent != self.current_percentage:
            self.percent.setText(f'{percent} %')
            self.percent.update()
            self.current_percentage = percent

        if percent <= 10:
            asset_name = '10'
        elif 40 > percent >= 15:
            asset_name = '25'
        elif 65 > percent >= 40:
            asset_name = '50'
        elif 90 > percent >= 65:
            asset_name = '75'
        else:
            asset_name = 'full'

        if charging != self.last_charge_state:
            if charging:
                asset_name = 'charging_' + asset_name

            self.last_charge_state = charging

        if asset_name.endswith('_'):
            asset_name = 'unknown'

        asset = f':/battery/{asset_name}.png'
        if self._asset != asset:
            pixmap = QPixmap(asset)
            self.icon.setPixmap(pixmap.scaled(41, 21))
            self.icon.update()
