from PyQt6 import QtCore

mj, mi, bu = [int(v) for v in QtCore.qVersion().split('.')]
print(f'Using Qt {mj}.{mi}.{bu}')

# import compiled qt resource data
from puffco import resources
