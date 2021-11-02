import asyncio
from bleak import BleakScanner

scanner = BleakScanner()  # scanning_mode='passive')


async def main():
    x = await scanner.discover()
    for dev in x:
        if dev.rssi <= -75:
            continue

        print('Name:', str(dev).split(': ')[1])
        print('address:', dev.address)
        print('rssi:', dev.rssi)
        print('details:', dev.details)
        print('metadata:', dev.metadata)
        print()

asyncio.run(main())
