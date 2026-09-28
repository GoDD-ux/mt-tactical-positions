# -*- coding: utf-8 -*-
"""Тактики из режима «Топография» (scripts/maps_training_tactical_maps.xml).

Модуль не зависит от клиента: на вход приходят обычные dict/list, которые
game-часть собирает из DataSection. Так его можно гонять в unittest.
"""
import re
from collections import namedtuple

# миникарта в интерфейсе «Топографии» - 570x570, координаты точек - левый верхний
# угол иконки 12x12 (см. maps_training_tactical_maps_config._POINT_OFFSET)
LOBBY_MINIMAP_SIZE = 570.0
POINT_OFFSET = 6

Point = namedtuple('Point', 'id x y')
Tactic = namedtuple('Tactic', 'geometry team vehicle_class points')


def to_world(point, bottom_left, upper_right):
    """Пиксели миникарты лобби -> координаты (x, z) на арене.

    Ось y у картинки направлена вниз, а z на арене - вверх, поэтому она переворачивается.
    """
    u = (point.x + POINT_OFFSET) / LOBBY_MINIMAP_SIZE
    v = (point.y + POINT_OFFSET) / LOBBY_MINIMAP_SIZE
    left, bottom = bottom_left
    right, top = upper_right
    return left + u * (right - left), top - v * (top - bottom)


def _parse_position(value):
    if isinstance(value, (tuple, list)):
        return float(value[0]), float(value[1])
    x, y = value.split()
    return float(x), float(y)


def parse_maps(maps):
    """maps - список карт в том же виде, что и в xml:
    [{'geometryName': ..., 'teams': [{'id': 1, 'configs': [{'type': ..., 'points': [...]}]}]}]
    """
    tactics = []
    for map_data in maps:
        geometry = map_data['geometryName']
        for team in map_data.get('teams', ()):
            for config in team.get('configs', ()):
                points = []
                for point in config.get('points', ()):
                    x, y = _parse_position(point['position'])
                    points.append(Point(point['id'], x, y))
                tactics.append(Tactic(geometry, int(team['id']), config['type'], tuple(points)))
    return tactics


class TacticsIndex(object):

    def __init__(self, tactics):
        self._tactics = dict(((t.geometry, t.team, t.vehicle_class), t) for t in tactics)

    def __len__(self):
        return len(self._tactics)

    def find(self, geometry, team, vehicle_class):
        return self._tactics.get((geometry, team, vehicle_class))

    def maps(self):
        return sorted(set(key[0] for key in self._tactics))

    def classes(self):
        return sorted(set(key[2] for key in self._tactics))


_TAG = re.compile(r'</?[\w.]+>')


def clean_description(text):
    """В описаниях тактик названия точек обёрнуты в теги вида <a_ht_gorge>ущелье</a_ht_gorge>,
    а абзацы разделены %(p). В чате боя это не нужно."""
    text = _TAG.sub(u'', text)
    parts = [part.strip() for part in text.split(u'%(p)')]
    return [part for part in parts if part]
