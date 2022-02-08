from PyQt5.QtBluetooth import QBluetoothDeviceDiscoveryAgent, QBluetoothDeviceInfo
from PyQt5.QtCore import QObject, QUuid

from puffco.bluetooth import PuffcoCharacteristics
SCAN_TIMEOUT_MS = 2500


class BLEScanner(QObject):
    def __init__(self, handle):
        QObject.__init__(self)
        self._handle = handle
        self._found_devices = []

        self.agent = QBluetoothDeviceDiscoveryAgent()
        self.agent.setLowEnergyDiscoveryTimeout(SCAN_TIMEOUT_MS)
        self.agent.finished.connect(self._handle.device_scan_complete)
        self.agent.deviceDiscovered.connect(self.add_device)

    def add_device(self, device):
        if device.coreConfigurations() & QBluetoothDeviceInfo.CoreConfiguration.LowEnergyCoreConfiguration:
            services, _ = device.serviceUuids()
            if QUuid(PuffcoCharacteristics.UUID) in services and device not in self._found_devices:
                self._found_devices.append(device)
                self._handle.devices.append(QBluetoothDeviceInfo(device))

    def stop(self):
        return self.agent.stop()

    def scan(self):
        print('>> Scanning...')
        self.agent.start(QBluetoothDeviceDiscoveryAgent.DiscoveryMethod(2))
