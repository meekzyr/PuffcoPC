from PyQt5.QtCore import QObject, pyqtSignal
from concurrent.futures import Future


class ReadFuture(Future):
    def __init__(self):
        Future.__init__(self)

    def __call__(self, result):
        self.ret = result
        self.set_result(result)


class Worker(QObject):
    finished = pyqtSignal()

    def __init__(self, func, *args, **kwargs):
        super(Worker, self).__init__(parent=None)

        self._func = func
        self._args = args
        self._kwargs = kwargs
        self.result = None

    def run(self):
        self.result = self._func(*self._args, **self._kwargs)
        self.finished.emit()
