from PyQt5.QtWidgets import QFrame, QPushButton


class HeatProfiles(QFrame):
    def __init__(self, parent=None):
        super(HeatProfiles, self).__init__(parent)
        self.setStyleSheet('background: transparent;')
        self.setVisible(False)
        self.preheatTestBtn = QPushButton('TEST2', self)
        self.preheatTestBtn.setGeometry(310, 20, 113, 32)

    async def fill(self):
        print(self.parent().PROFILES)
