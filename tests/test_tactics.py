# -*- coding: utf-8 -*-
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'mod', 'scripts', 'client', 'gui'))

from tactical_positions.tactics import (Point, TacticsIndex, clean_description,  # noqa: E402
                                        parse_maps, to_world)

MAPS = [{
    'geometryName': '01_karelia',
    'teams': [
        {'id': 1, 'configs': [
            {'type': 'heavyTank', 'points': [
                {'id': 'a_ht_gorge', 'position': '63 67'},
                {'id': 'a_ht_plateau', 'position': (154, 118)},
            ]},
            {'type': 'mediumTank', 'points': []},
        ]},
        {'id': 2, 'configs': [
            {'type': 'heavyTank', 'points': [{'id': 'b_ht_ledge', 'position': '400 300'}]},
        ]},
    ],
}]

BL, UR = (-500.0, -500.0), (500.0, 500.0)


class ParseTest(unittest.TestCase):

    def setUp(self):
        self.index = TacticsIndex(parse_maps(MAPS))

    def test_find(self):
        tactic = self.index.find('01_karelia', 1, 'heavyTank')
        self.assertEqual([p.id for p in tactic.points], ['a_ht_gorge', 'a_ht_plateau'])
        self.assertEqual(tactic.points[1], Point('a_ht_plateau', 154.0, 118.0))

    def test_teams_are_separate(self):
        self.assertEqual(self.index.find('01_karelia', 2, 'heavyTank').points[0].id, 'b_ht_ledge')

    def test_missing(self):
        self.assertIsNone(self.index.find('01_karelia', 1, 'SPG'))
        self.assertIsNone(self.index.find('02_malinovka', 1, 'heavyTank'))

    def test_empty_points_kept(self):
        self.assertEqual(self.index.find('01_karelia', 1, 'mediumTank').points, ())

    def test_summary(self):
        self.assertEqual(len(self.index), 3)
        self.assertEqual(self.index.maps(), ['01_karelia'])
        self.assertEqual(self.index.classes(), ['heavyTank', 'mediumTank'])


class ToWorldTest(unittest.TestCase):

    def test_corners(self):
        # с учётом смещения иконки левый верхний угол картинки - это точка (-6, -6)
        self.assertEqual(to_world(Point('', -6, -6), BL, UR), (-500.0, 500.0))
        self.assertEqual(to_world(Point('', 564, 564), BL, UR), (500.0, -500.0))

    def test_center(self):
        x, z = to_world(Point('', 279, 279), BL, UR)
        self.assertAlmostEqual(x, 0)
        self.assertAlmostEqual(z, 0)

    def test_not_square_arena(self):
        x, z = to_world(Point('', 279, 279), (0.0, -200.0), (800.0, 600.0))
        self.assertAlmostEqual(x, 400)
        self.assertAlmostEqual(z, 200)

    def test_team_base_matches_arena_def(self):
        # база второй команды на Карелии: в arena_defs (-401.3, -399.9),
        # в разметке «Топографии» иконка базы 48x48 стоит в (33, 496)
        x, z = to_world(Point('', 33 + 24 - 6, 496 + 24 - 6), BL, UR)
        self.assertAlmostEqual(x, -401.3, delta=15)
        self.assertAlmostEqual(z, -399.9, delta=15)


class DescriptionTest(unittest.TestCase):

    def test_tags_and_paragraphs(self):
        text = (u'Ключевой точкой этой тактики является <a_ht_gorge>ущелье</a_ht_gorge>.'
                u'%(p)Займите позицию у <b_ht_ledge>выступа</b_ht_ledge>.%(p)')
        self.assertEqual(clean_description(text), [
            u'Ключевой точкой этой тактики является ущелье.',
            u'Займите позицию у выступа.',
        ])

    def test_plain_text(self):
        self.assertEqual(clean_description(u'просто текст'), [u'просто текст'])


if __name__ == '__main__':
    unittest.main()
