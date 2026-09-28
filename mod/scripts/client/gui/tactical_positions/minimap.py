# -*- coding: utf-8 -*-
import logging

import BigWorld
import Math
import ResMgr
from gui.Scaleform.daapi.view.battle.shared.minimap import settings
from gui.Scaleform.daapi.view.battle.shared.minimap.common import EntriesPlugin
from gui.Scaleform.daapi.view.battle.shared.minimap.component import MinimapComponent
from gui.battle_control import minimap_utils
from helpers import i18n
from messenger import MessengerEntry

from .tactics import TacticsIndex, clean_description, parse_maps, to_world

logger = logging.getLogger('tactical_positions')

TACTICS_XML = 'scripts/maps_training_tactical_maps.xml'
PLUGIN_NAME = 'tacticalPositions'
# та же метка, что ставит игрок через радиальное меню, она уже есть во flash-миникарте
SYMBOL = settings.ENTRY_SYMBOL_NAME.NAVIGATION_POINT_MARKER
CONTAINER = settings.CONTAINER_NAME.EQUIPMENTS
MARKER_SCALE = 0.8
# чат боя переключается на боевой контекст чуть позже миникарты
CHAT_DELAY = 3.0

_index = None


def _sectionToMaps(section):
    maps = []
    for mapSection in section['maps'].values():
        teams = []
        for teamSection in mapSection['teams'].values():
            configs = []
            for configSection in teamSection['configs'].values():
                pointsSection = configSection['points']
                points = []
                if pointsSection is not None:
                    for p in pointsSection.values():
                        position = p.readVector2('position')
                        points.append({'id': p.readString('id'), 'position': (position.x, position.y)})
                configs.append({'type': configSection.readString('type'), 'points': points})
            teams.append({'id': teamSection.readInt('id'), 'configs': configs})
        maps.append({'geometryName': mapSection.readString('geometryName'), 'teams': teams})
    return maps


def getIndex():
    global _index
    if _index is None:
        section = ResMgr.openSection(TACTICS_XML)
        if section is None:
            logger.error('%s not found, positions are disabled', TACTICS_XML)
            _index = TacticsIndex([])
        else:
            _index = TacticsIndex(parse_maps(_sectionToMaps(section)))
            ResMgr.purge(TACTICS_XML)
            logger.info('loaded %d tactics for maps: %s', len(_index), ', '.join(_index.maps()))
    return _index


def _text(geometry, key):
    return i18n.makeString('#maps_training:%s/%s' % (geometry, key))


class TacticalPositionsPlugin(EntriesPlugin):

    def start(self):
        super(TacticalPositionsPlugin, self).start()
        try:
            self._showTactic()
        except Exception:
            logger.exception('cannot show positions')

    def _showTactic(self):
        geometry = self._arenaVisitor.type.getGeometryName()
        team = self._arenaDP.getNumberOfTeam()
        vehicle = self._arenaDP.getVehicleInfo().vehicleType
        tactic = getIndex().find(geometry, team, vehicle.classTag)
        if tactic is None:
            logger.debug('no tactic for %s, team %s, %s', geometry, team, vehicle.classTag)
            return

        bottomLeft, upperRight = self._arenaVisitor.type.getBoundingBox()
        bottomLeft, upperRight = (bottomLeft[0], bottomLeft[1]), (upperRight[0], upperRight[1])
        for point in tactic.points:
            x, z = to_world(point, bottomLeft, upperRight)
            matrix = minimap_utils.makePositionAndScaleMatrix(Math.Vector3(x, 0, z),
                                                              (MARKER_SCALE, 1.0, MARKER_SCALE))
            self._addEntryEx(point.id, SYMBOL, CONTAINER, matrix=matrix, active=True,
                             transformProps=settings.TRANSFORM_FLAG.FULL)
        BigWorld.callback(CHAT_DELAY, lambda: self._printToChat(tactic))

    def _printToChat(self, tactic):
        if self._arenaDP is None:  # бой уже закончился
            return
        prefix = 'team%d/%s/' % (tactic.team, tactic.vehicle_class)
        title = _text(tactic.geometry, prefix + 'title')
        names = u', '.join(_text(tactic.geometry, p.id) for p in tactic.points)
        lines = [u'<font color="#E9C46A">Тактика: %s</font>' % title,
                 u'Позиции на миникарте: %s' % names]
        lines.extend(clean_description(_text(tactic.geometry, prefix + 'descr')))
        chat = MessengerEntry.g_instance.gui
        for line in lines:
            chat.addClientMessage(line)


def install():
    original = MinimapComponent._setupPlugins

    def _setupPlugins(self, arenaVisitor):
        setup = original(self, arenaVisitor)
        setup[PLUGIN_NAME] = TacticalPositionsPlugin
        return setup

    MinimapComponent._setupPlugins = _setupPlugins
    return original


def uninstall(original):
    MinimapComponent._setupPlugins = original
