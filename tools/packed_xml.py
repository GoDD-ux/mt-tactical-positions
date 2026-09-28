"""Чтение упакованного XML движка BigWorld (файлы .xml внутри .pkg клиента).

Формат: сигнатура 0x62A14E45, байт версии, словарь имён тегов (строки через \\0,
заканчивается пустой строкой), дальше дерево элементов. У каждого элемента:
число детей (u16), дескриптор собственного значения (u32) и дескрипторы детей
(u16 индекс имени + u32). В дескрипторе младшие 28 бит - смещение конца данных,
старшие 4 - тип: 0 элемент, 1 строка, 2 int, 3 float[], 4 bool, 5 blob.
"""
import base64
import struct

MAGIC = b'\x45\x4e\xa1\x62'


class Element(object):

    def __init__(self, value, children):
        self.value = value
        self.children = children  # [(name, Element | значение)]

    def __getitem__(self, name):
        for key, child in self.children:
            if key == name:
                return child
        return None

    def all(self, name):
        return [child for key, child in self.children if key == name]

    def text(self, name, default=None):
        child = self[name]
        return default if child is None else child.value


class _Reader(object):

    def __init__(self, data):
        if data[:4] != MAGIC:
            raise ValueError('not a packed xml')
        self.data = data
        self.pos = 5
        self.names = []
        while True:
            end = data.index(b'\x00', self.pos)
            name = data[self.pos:end].decode('ascii')
            self.pos = end + 1
            if not name:
                break
            self.names.append(name)

    def _unpack(self, fmt):
        value = struct.unpack_from(fmt, self.data, self.pos)[0]
        self.pos += struct.calcsize(fmt)
        return value

    def element(self):
        count = self._unpack('<H')
        own = self._unpack('<I')
        descriptors = [(self._unpack('<H'), self._unpack('<I')) for _ in range(count)]
        base = self.pos
        offset = own & 0x0FFFFFFF
        value = self._value(own >> 28, base, base + offset)
        children = []
        for name_index, descriptor in descriptors:
            end = descriptor & 0x0FFFFFFF
            kind = descriptor >> 28
            if kind == 0:
                self.pos = base + offset
                child = self.element()
            else:
                child = Element(self._value(kind, base + offset, base + end), [])
            children.append((self.names[name_index], child))
            offset = end
        self.pos = base + offset
        return Element(value, children)

    def _value(self, kind, start, end):
        raw = self.data[start:end]
        if kind == 1:
            return raw.decode('utf-8')
        if kind == 2:
            if not raw:
                return 0
            return struct.unpack({1: '<b', 2: '<h', 4: '<i', 8: '<q'}[len(raw)], raw)[0]
        if kind == 3:
            return list(struct.unpack('<%df' % (len(raw) // 4), raw))
        if kind == 4:
            return raw == b'\x01'
        if kind == 5:
            return base64.b64encode(raw).decode('ascii')
        return None


def parse(data):
    return _Reader(data).element()
