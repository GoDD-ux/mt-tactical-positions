# -*- coding: utf-8 -*-
"""Рисует позиции из «Топографии» поверх настоящих миникарт из установленного клиента.

    python tools/preview.py C:/Games/Tanki            # все карты в docs/preview/
    python tools/preview.py C:/Games/Tanki 01_karelia

Нужен для проверки формулы перевода координат без захода в бой: если точка
«Ущелье» оказалась в ущелье, значит пересчёт верный. Данные и картинки берутся
из клиента пользователя и в репозиторий не кладутся (кроме пары скриншотов).
Работает на Python 3, нужен Pillow.
"""
import argparse
import gettext
import io
import os
import sys
import zipfile

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'mod', 'scripts', 'client', 'gui'))

import packed_xml  # noqa: E402
from tactical_positions.tactics import TacticsIndex, parse_maps, to_world  # noqa: E402

TACTICS_XML = 'scripts/maps_training_tactical_maps.xml'
SIZE = 800
COLORS = {'heavyTank': (231, 111, 81), 'mediumTank': (233, 196, 106)}
TEAM_NAMES = {1: u'команда 1', 2: u'команда 2'}
CLASS_NAMES = {'heavyTank': u'ТТ', 'mediumTank': u'СТ'}


class Client(object):

    def __init__(self, game_dir):
        self.packages = os.path.join(game_dir, 'res', 'packages')
        self.scripts = zipfile.ZipFile(os.path.join(self.packages, 'scripts.pkg'))
        mo = os.path.join(game_dir, 'res', 'text', 'ru', 'lc_messages', 'maps_training.mo')
        with open(mo, 'rb') as f:
            self.texts = gettext.GNUTranslations(f)

    def tactics(self):
        root = packed_xml.parse(self.scripts.read(TACTICS_XML))
        maps = []
        for map_el in root['maps'].all('map'):
            teams = []
            for team_el in map_el['teams'].all('team'):
                configs = []
                for config_el in team_el['configs'].all('config'):
                    points_el = config_el['points']
                    points = [{'id': p.text('id'), 'position': p.text('position')}
                              for p in (points_el.all('point') if points_el else [])]
                    configs.append({'type': config_el.text('type'), 'points': points})
                teams.append({'id': team_el.text('id'), 'configs': configs})
            maps.append({'geometryName': map_el.text('geometryName'), 'teams': teams})
        return TacticsIndex(parse_maps(maps))

    def bounding_box(self, geometry):
        arena = packed_xml.parse(self.scripts.read('scripts/arena_defs/%s.xml' % geometry))
        box = arena['boundingBox']
        return _vector(box.text('bottomLeft')), _vector(box.text('upperRight'))

    def minimap(self, geometry):
        package = zipfile.ZipFile(os.path.join(self.packages, '%s.pkg' % geometry))
        data = package.read('spaces/%s/mmap.dds' % geometry)
        return Image.open(io.BytesIO(data)).convert('RGB')

    def text(self, geometry, key):
        return self.texts.gettext('%s/%s' % (geometry, key))


def _vector(value):
    if isinstance(value, str):
        value = value.split()
    return float(value[0]), float(value[1])


def _font(size):
    for name in ('segoeuib.ttf', 'arialbd.ttf', 'DejaVuSans-Bold.ttf'):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def render(client, index, geometry, team, vehicle_class):
    tactic = index.find(geometry, team, vehicle_class)
    image = client.minimap(geometry).resize((SIZE, SIZE))
    draw = ImageDraw.Draw(image, 'RGBA')
    bottom_left, upper_right = client.bounding_box(geometry)
    width = upper_right[0] - bottom_left[0]
    height = upper_right[1] - bottom_left[1]
    color = COLORS[vehicle_class]
    font = _font(18)

    for point in tactic.points:
        x, z = to_world(point, bottom_left, upper_right)
        # обратно в пиксели картинки - так проверяется вся цепочка через координаты арены
        px = (x - bottom_left[0]) / width * SIZE
        py = (upper_right[1] - z) / height * SIZE
        draw.ellipse((px - 11, py - 11, px + 11, py + 11), fill=color + (230,), outline=(0, 0, 0, 255), width=2)
        label = client.text(geometry, point.id)
        label_width = draw.textlength(label, font=font)
        # у правого края подпись переносим влево от точки, иначе её обрежет
        lx = px + 15 if px + 15 + label_width < SIZE else px - 15 - label_width
        ly = min(max(py - 11, 62), SIZE - 26)
        draw.text((lx, ly), label, font=font, fill=(255, 255, 255, 255),
                  stroke_width=3, stroke_fill=(0, 0, 0, 255))

    title = u'%s · %s · %s' % (client.text(geometry, 'upperName'), TEAM_NAMES[team], CLASS_NAMES[vehicle_class])
    tactic_name = client.text(geometry, 'team%d/%s/title' % (team, vehicle_class))
    draw.rectangle((0, 0, SIZE, 58), fill=(0, 0, 0, 170))
    draw.text((12, 6), title, font=_font(20), fill=(255, 255, 255, 255))
    draw.text((12, 32), tactic_name, font=_font(18), fill=color + (255,))
    return image


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('game_dir')
    parser.add_argument('maps', nargs='*')
    parser.add_argument('--out', default=os.path.join(HERE, '..', 'docs', 'preview'))
    args = parser.parse_args()

    client = Client(args.game_dir)
    index = client.tactics()
    if not os.path.isdir(args.out):
        os.makedirs(args.out)
    for geometry in args.maps or index.maps():
        for team in (1, 2):
            for vehicle_class in index.classes():
                if index.find(geometry, team, vehicle_class) is None:
                    continue
                image = render(client, index, geometry, team, vehicle_class)
                name = '%s_team%d_%s.png' % (geometry, team, vehicle_class)
                image.save(os.path.join(args.out, name))
                print(name)


if __name__ == '__main__':
    main()
