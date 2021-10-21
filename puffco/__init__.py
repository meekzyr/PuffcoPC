# import compiled qt resource data
from puffco import resources

mj, mi, bu = resources.qt_version
print(f'Using Qt {mj}.{mi}.{bu}')
