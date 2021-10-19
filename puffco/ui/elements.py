from PyQt5.QtWidgets import QAbstractButton, QLabel, QGraphicsBlurEffect
from PyQt5.QtGui import QPainter, QColor, QPixmap
from PyQt5.QtCore import Qt


class ProfileButton(QAbstractButton):
    def __init__(self, parent, pixmap, geom):
        super(ProfileButton, self).__init__(parent)
        self.setGeometry(*geom)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._pixmap = pixmap
        self.profile_name = QLabel('', self)
        self.profile_name.move(5, 5)
        self.temperature = QLabel('', self)
        self.temperature.move(5, 80)
        self.duration = QLabel('', self)
        self.duration.move(310, 80)
        self.duration.adjustSize()

        self.glow = QLabel('', self)
        # TODO: the image below is meant for the page when you select a profile.. recreate the proper arc traj+glow
        self.glow.setPixmap(QPixmap(':/assets/profile-glow.png'))
        self.glow.move(150, -30)
        b = QGraphicsBlurEffect()
        b.setBlurRadius(5)
        self.glow.setGraphicsEffect(b)
        self.glow.adjustSize()
        self.color = None

    def pixmap(self):
        return self._pixmap

    def set_pixmap_color(self, color):
        self.color = color
        # color our glow effect
        pm = self.glow.pixmap()
        painter = QPainter(pm)
        painter.setOpacity(15)
        painter.setCompositionMode(painter.CompositionMode_SourceIn)
        painter.fillRect(pm.rect(), QColor(*color))
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
        painter.setCompositionMode(painter.CompositionMode_Overlay)
        if self.color:
            painter.fillRect(event.rect(), QColor(*self.color))

        painter.drawPixmap(event.rect(), self._pixmap)

    def sizeHint(self):
        return self._pixmap.size()
