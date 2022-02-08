from PyQt5.QtBluetooth import QBluetoothUuid, QLowEnergyCharacteristic, QLowEnergyService
from PyQt5.QtCore import QObject


class CharacteristicInfo(QObject):
    def __init__(self, service: QLowEnergyService, characteristic: QLowEnergyCharacteristic):
        QObject.__init__(self)
        self.service = service
        self.characteristic = characteristic

    def set_characteristic(self, characteristic: QLowEnergyCharacteristic):
        self.characteristic = characteristic

    @property
    def name(self) -> str:
        name = self.characteristic.name()
        if name != '':
            return name

        descriptors = self.characteristic.descriptors()
        for descriptor in descriptors:
            if descriptor.type() == QBluetoothUuid.CharacteristicUserDescription:
                name = str(descriptor.value())
                break

        if name == '':
            name = 'Unknown'

        return name

    @property
    def uuid(self) -> str:
        return self.characteristic.uuid().toString()

    @property
    def value(self) -> str:
        result = self.characteristic.value()
        if result.isEmpty():
            return None

        return result.data()

    @property
    def handle(self) -> str:
        return '0x' + str(self.characteristic.handle())

    @property
    def permissions(self) -> str:
        properties = ''
        permission = self.characteristic.properties()
        if permission & QLowEnergyCharacteristic.PropertyType.Read:
            properties += ' Read'
        if permission & QLowEnergyCharacteristic.PropertyType.Write:
            properties += ' Write'
        if permission & QLowEnergyCharacteristic.PropertyType.Notify:
            properties += ' Notify'
        if permission & QLowEnergyCharacteristic.PropertyType.Indicate:
            properties += ' Indicate'
        if permission & QLowEnergyCharacteristic.PropertyType.ExtendedProperty:
            properties += ' ExtendedProperty'
        if permission & QLowEnergyCharacteristic.PropertyType.Broadcasting:
            properties += ' Broadcast'
        if permission & QLowEnergyCharacteristic.PropertyType.WriteNoResponse:
            properties += ' WriteNoResp'
        if permission & QLowEnergyCharacteristic.PropertyType.WriteSigned:
            properties += ' WriteSigned'
        return f'( {properties} )'
