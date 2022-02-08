import struct

from asyncio import ensure_future
from PyQt5.QtCore import QObject, QThread

from .characteristic import CharacteristicInfo
from .constants import *
from .controller import BLEController
from .scanner import BLEScanner


def parse(data, fmt='f'):
    _struct = struct.unpack(fmt, data)
    remove = ['(', ',', ')']
    for chars in remove:
        _struct = str(_struct).replace(chars, "")
    return _struct


def _worker_done(callback, worker, thread):
    if callback:
        try:
            callback(worker.result)
        except TypeError:  # invalid amount of arguments
            callback()

    thread.quit()
    worker.deleteLater()


def thread_operation(worker, callback=None, start=False):
    thread = QThread()
    worker.moveToThread(thread)  # move the worker to the Qt thread

    thread.started.connect(worker.run)
    worker.finished.connect(lambda: _worker_done(callback, worker, thread))
    thread.finished.connect(thread.deleteLater)
    if start:
        thread.start()

    return thread, worker


class BluetoothHandle(QObject):
    connected = False

    def __init__(self, callback):
        QObject.__init__(self)
        self.controller = BLEController(self)
        self.scanner = BLEScanner(self)
        self.devices = []
        self.fetch_callback = callback

    def start(self):
        self.scanner.scan()

    def device(self):
        return self.controller.device

    @property
    def is_connected(self):
        return self.connected is True

    def device_scan_complete(self):
        self.scanner.agent.stop()

        # TODO: handle multiple devices; handle BT disabled + finding 0 devices
        from .device import PeakPro

        print(f'Found {len(self.devices)} Puffco Peak Pro(s):')
        for i, ppp in enumerate(self.devices):
            print(f'Device #{i + 1}:')
            print(f'  Name: {ppp.name()}')
            print(f'  MAC Address: {ppp.address().toString()}')
            peak_pro_device = PeakPro(ppp, self.controller)
            peak_pro_device.ready.connect(self.fetch_callback)

            self.controller.connect(peak_pro_device)
            break

    def send_lantern_brightness(self, *args):
        device = self.device()
        if device is None:
            return

        ensure_future(device.send_lantern_brightness(*args))
