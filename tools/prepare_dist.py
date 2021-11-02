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
    '_asyncio.pyd',
    '_socket.pyd',
    '_overlapped.pyd',
    'clr.pyd',
    'select.pyd',
)
included_directories = ('pyqt5', 'bleak_winrt', 'pil')

count = 0
for file in build_dir:
    file = file.lower()
    if file.endswith('.exe') or file.startswith('python') or (file in included_directories) or \
            (file in used_libraries) or (file in used_python_libraries):
        continue

    count += 1
    file = f'puffco.dist/{file}'
    if os.path.isdir(file):
        shutil.rmtree(file, ignore_errors=True)
    else:
        os.unlink(file)


print(f'Removed {count} unused files. Compressing dist directory..')
fmt = {'win32': 'zip', 'linux': 'gztar', 'darwin': 'zip'}[sys.platform]
shutil.make_archive('release', format=fmt, root_dir='puffco.dist/', base_dir=None)
print('Done.')
