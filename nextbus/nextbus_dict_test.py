from _ast import Dict
from unittest import TestCase

from nextbus import NextBus
from nextbus_dict import Agency, Route
import nextbus_dict

__author__ = 'lwhite'

class TestNextbus(TestCase):
    def test_agencies_dict(self):
        result = nextbus_dict.agencies_dict()
        self.assertIsNotNone(result)

    def test_ensure_mbta_exists(self):
        result = nextbus_dict.agencies_dict()
        self.assertIsNotNone(result)
        self.assertIsInstance(result["mbta"], Agency)

    def test_routes_as_dict(self):
        result = nextbus_dict.agencies_dict()
        self.assertIsNotNone(result)
        a = result["mbta"]
        self.assertIsInstance(a, Agency)
        self.assertIsNotNone(a.routes)
        self.assertIsInstance(a.routes, dict)
        self.assertIsInstance(a.routes['87'], Route)
