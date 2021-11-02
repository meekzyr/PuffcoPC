import os
import sys
import shutil

if not os.path.exists('puffco.dist/'):
    sys.exit('No build files found')

build_dir = os.listdir('puffco.dist/')

used_libraries = (
    'bleakuwpbridge.dll',
    'qt5core.dll',
    'qt5gui.dll',
    'qt5widgets.dll',
    'msvcp140.dll',
    'vcruntime140.dll',
)

used_python_libraries = (
    # windows
    '_asyncio.pyd',
    '_socket.pyd',
    '_overlapped.pyd',
    'clr.pyd',
    'select.pyd',
)
included_directories = ('pyqt5', 'bleak_winrt', 'pil')

linux_libraries = (
    '_asyncio.so',
    '_contextvars.so',
    'libdus.so',
    'libicudata.so',
    'libicui18n.so',
    'libicuuc.so',
    'libqt5core.so',
    'libqt5dbus.so',
    'libqt5gui.so',
    'libqt5widgets.so',
    'libqt5xcbqpa.so',
)

print(os.getcwd())
total = included_directories + used_libraries + used_python_libraries + linux_libraries

count = 0
for file in build_dir:
    _file = file.lower()
    if _file.startswith('puffco') or _file.startswith('python') or _file in total:
        continue

    file = f'puffco.dist/{file}'
    if os.path.isdir(file) and _file in included_directories:
        continue
    elif '.' in _file and _file[:_file.rindex('.')] in total:
        continue

    count += 1
    if os.path.isdir(file):
        shutil.rmtree(file, ignore_errors=True)
    else:
        os.unlink(file)


print(f'Removed {count} unused files. Compressing dist directory..')
fmt = {'win32': 'zip', 'linux': 'gztar', 'darwin': 'zip'}[sys.platform]
shutil.make_archive('release', format=fmt, root_dir='puffco.dist/', base_dir=None)
print('Done.')
