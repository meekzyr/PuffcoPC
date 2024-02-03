class Buffer(object):
    def __init__(self, init_value):
        if type(init_value) == int:
            self.data = bytearray(init_value)
            size = init_value
        else:
            if not isinstance(init_value, bytearray):
                self.data = bytearray(init_value)
            else:
                self.data = init_value
            size = len(init_value)
        self.size = size
        self.encoding = 'utf-8'

    # https://nodejs.org/api/buffer.html#buffer_buf_copy_target_targetstart_sourcestart_sourceend
    def copy(self, target_buf, target_start_pos=0, source_start_pos=0, source_end_pos=None):
        return self.copy_to_buffer(
            self.data,
            target_buf,
            target_start_pos,
            source_start_pos, source_end_pos
        )

    @staticmethod
    def copy_to_buffer(source_data, target_buf, target_start_pos=0, source_start_pos=0, source_end_pos=None):
        if source_end_pos is None:
            source_end_pos = len(source_data)
        target_available_bytes = target_buf.length() - target_start_pos - 1
        source_bytes_num = source_end_pos - source_start_pos
        copied_bytes_num = 0
        if target_available_bytes < source_bytes_num:
            real_source_end_pos = source_start_pos + target_available_bytes + 1
            copied_bytes_num = target_available_bytes
        else:
            real_source_end_pos = source_end_pos
            copied_bytes_num = source_bytes_num
        target_end_pos = target_start_pos + source_bytes_num
        target_buf.data[target_start_pos:target_end_pos] = (
            source_data[source_start_pos:real_source_end_pos])
        return copied_bytes_num

    # https://nodejs.org/api/buffer.html#buffer_buf_fill_value_offset_end_encoding
    def fill(self, value, start_pos=0, end_pos=None):
        if end_pos is None:
            end_pos = self.size
        bytes_number = end_pos - start_pos
        self.data[start_pos:end_pos] = bytes([value for i in range(end_pos - start_pos)])

    # https://nodejs.org/api/buffer.html#buffer_buf_indexof_value_byteoffset_encoding
    def index_of(self, value, pos):
        return self.data.find(value, pos)

    # https://nodejs.org/api/buffer.html#buffer_buf_length
    def length(self):
        return self.size

    def readUInt8(self, pos):
        return self.readUIntLE(pos, 1)

    def readUInt16LE(self, pos):
        return self.readUIntLE(pos, 2)

    def readUIntLE(self, pos, byte_len=1):
        value_bytes = self.data[pos:pos + byte_len]
        return int.from_bytes(value_bytes, byteorder='little')

    def slice(self, start_pos=0, end_pos=None):
        if end_pos is None:
            end_pos = self.size
        return Buffer(self.data[start_pos:end_pos])

    # https://nodejs.org/api/buffer.html#buffer_buf_tostring_encoding_start_end
    def toString(self, encoding='utf-8', start_pos=0, end_pos=None):
        if end_pos is None:
            end_pos = self.size
        return self.data[start_pos:end_pos].decode(encoding, errors='ignore')

    # https://nodejs.org/api/buffer.html#buffer_buf_write_string_offset_length_encoding
    def write(self, str_value, pos=0, length=None):
        if str_value is None:
            str_value = ''
        if length is None:
            length = len(self.data) - pos
        value_bytes = bytes(str_value, self.encoding)
        bytes_num = len(value_bytes)
        end_pos = 0
        if len(str_value) == bytes_num:
            if bytes_num > length:
                bytes_num = length
            if bytes_num <= self.size - pos:
                end_pos = pos + bytes_num
            else:  # write partially
                end_pos = self.size
                bytes_num = self.size - pos
            self.data[pos:end_pos] = value_bytes[0:bytes_num]
        else:  # multiple bytes chars in string
            raise NotImplementedError('Not implemented case')

        return bytes_num

    # https://nodejs.org/api/buffer.html#buffer_buf_writeint8_value_offset
    def writeUInt8(self, int_value, pos):
        return self.writeUIntLE(int_value, pos, 1)

    # https://nodejs.org/api/buffer.html#buffer_buf_writeuintle_value_offset_bytelength
    def writeUIntLE(self, int_value, pos, byte_len):
        if int_value is None:
            int_value = 0
        value_bytes = int_value.to_bytes(byte_len, byteorder='little')
        self.data[pos:pos + byte_len] = value_bytes
        return pos + byte_len

    # https://nodejs.org/api/buffer.html#buffer_buf_writeuint16le_value_offset
    def writeUInt16LE(self, int_value, pos):
        return self.writeUIntLE(int_value, pos, 2)

    # https://nodejs.org/api/buffer.html#buffer_buf_writeuint32le_value_offset
    def writeUInt32LE(self, int_value, pos):
        return self.writeUIntLE(int_value, pos, 4)
