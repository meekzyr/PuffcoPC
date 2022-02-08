from PyQt5.QtBluetooth import QBluetoothUuid, QLowEnergyController
from PyQt5.QtCore import QObject, pyqtSignal


class BLEController(QObject):
    console = pyqtSignal(str)
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    found_services = pyqtSignal()
    opened_service = pyqtSignal()
    core = None
    device = None

    def __init__(self, handle):
        QObject.__init__(self)
        self._handle = handle

    def device_connected(self, *args):
        self.connected.emit()
        self.core.discoverServices()

    def device_disconnected(self):
        print('Device disconnected')
        self.disconnected.emit()

    def device_error(self, error):
        print(f'[BLE Error]: {error} {str(error)}')
        self.console.emit(f'BLE Error: {error}')

    def _service_error(self, *args):
        print(f'_service_error {args}')

    def add_service(self, service_uid):
        if service_uid not in self.device.services:
            service = self.core.createServiceObject(service_uid)
            service.error.connect(self._service_error)
            self.device.services.append(service)

    def service_scan_done(self):
        print(f'Service scan complete.')
        self.found_services.emit()

    def connect(self, device):
        self.device = device
        print(f'Connecting to {self.device.name()}')
        self.core = QLowEnergyController.createCentral(self.device.qtd)
        self.core.connected.connect(self.device_connected)
        self.core.disconnected.connect(self.device_disconnected)
        self.core.error.connect(self.device_error)
        self.core.serviceDiscovered.connect(self.add_service)
        self.core.discoveryFinished.connect(self.service_scan_done)
        self.core.connectToDevice()
