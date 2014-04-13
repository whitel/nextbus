# import datetime
# import re
# import xml.etree.ElementTree as ET
#
# from configurati import attrs

from nextbus import NextBus
import requests

def agencies_dict():
    """Get all agencies tracked by NextBus

    Returns
    -------
    agencies : [Agency]
    """
    result = NextBus().agencies_raw()
    return dict((a.tag, a) for a in [Agency(**e.attrs) for e in result if e.tag == 'agency'])

class Agency(object):
    """A single agency served by NextBus

    Parameters
    ----------
    tag : str
        unique identifier for this agency
    title : str
        human-readable name for this agency
    regionTitle : str
        area served by this agency (e.g. California-Northern)
    shortTitle : str
        a shorter human-readable name for this agency
    """
    def __init__(self, tag, title, regionTitle, shortTitle=None, **kwargs):
        self.tag          = str(tag)
        self.title        = str(title)
        self.short_title  = str(shortTitle or title)
        self.region_title = str(regionTitle)
        self._routes      = None

    @property
    def routes(self):
        """All routes this agency serves

        Returns
        -------
        routes : [Route]
        """
        if (self._routes is None):
            result = NextBus._fetch_xml({
                'command': 'routeList',
                'a': self.tag,
            })
            self._routes = dict((r.tag, r) for r in [Route(agency=self.tag, **e.attrs) for e in result if e.tag == 'route'])
        return self._routes

    def __str__(self):
        return "Agency: %s" % self.title
    def __repr__(self):
        return "Agency(tag=%s, title=%s, regionTitle=%s, shortTitle=%s)" % \
            (self.tag, self.title, self.region_title, self.short_title)

class Route(object):
  """A single transit route. e.g. SF MUNI's N bus

  Parameters
  ----------
  agency : str
      tag of agency running this route
  tag : str
      tag of this route
  title : str
      human-readable title for this route
  shortTitle : str
      short human-readable title for this route
  """
  def __init__(self, agency, tag, title, shortTitle=None, **kwargs):
    self.agency      = str(agency)
    self.tag         = str(tag)
    self.title       = str(title)
    self.short_title = str(shortTitle or title)

  @property
  def directions(self):
    """Get paths followed by each direction this bus can travel

    A bus typically travels 2 directions: inbound and outbound. These paths
    need not be the same, however, and there may be alternative paths of
    travel. This function lets one enumerate all such paths.

    Returns
    -------
    directions : [Direction]
    """
    result = NextBus._fetch_xml({
      'command': 'routeConfig',
      'a': self.agency,
      'r': self.tag,
    })
    stops = [Stop(route=self.tag, **e.attrs) for e in result[0].children
             if e.tag == 'stop']
    stops = { stop.tag: stop for stop in stops }

    directions = []
    for direction in [x for x in result[0].children if x.tag == 'direction']:
      directions.append(Direction(
        route=self.tag,
        stops=[stops[str(e.attrs.tag)] for e in direction.children],
        **direction.attrs
      ))

    return directions

  @property
  def stops(self):
    """Get all bus stops served by this route

    Returns
    -------
    stops : [Stop]
    """
    result = NextBus._fetch_xml({
      'command': 'routeConfig',
      'a': self.agency,
      'r': self.tag,
    })
    stops = [Stop(route=self.tag, **e.attrs) for e in result[0].children
             if e.tag == 'stop']
    return stops

  @property
  def schedule(self):
    """Get schedule for this route

    This call retrieves the times which this bus runs, and its expected arrival
    time at each stop.

    Result
    ------
    runs : [Run]
    """
    result = _fetch_xml({
      'command': 'schedule',
      'a': self.agency,
      'r': self.tag,
    })
    result = result.pop(0)

    stops = { stop.tag: stop for stop in self.stops }

    runs = []
    for run in [e for e in result.children if e.tag == 'tr']:
      run_ = []
      for stop in run.children:
        if stop.text == '--':
          time = None
        else:
          hour, minute, second = stop.text.split(":")
          time = datetime.time(int(hour), int(minute), int(second))

        run_.append(attrs({
          'stop': stops[str(stop.attrs.tag)],
          'time': time
        }))
      runs.append(Run(
        route=self.tag,
        stops=run_,
        scheduleClass=result.attrs.scheduleClass,
        serviceClass=result.attrs.serviceClass,
        direction=result.attrs.direction,
        **run.attrs
      ))

    return runs

  def __str__(self):
    return "Route: %s" % self.title

  def __repr__(self):
    return "Route(agency=%s, tag=%s, title=%s, shortTitle=%s)" % \
        (self.agency, self.tag, self.title, self.short_title)


class Run(object):
  """A single run of a particular route, with times of arrival

  Parameters
  ----------
  route : str
      tag of route this bus runs
  stops : [{"stop": Stop, "time": datetime.time}]
      list of stops and arrival times
  scheduleClass : str
  serviceClass : str
  direction : str
      tag of direction of travel
  blockID : str
  """
  def __init__(self, route, stops, scheduleClass, serviceClass, direction, blockID, **kwargs):
    self.route          = route
    self.stops          = stops
    self.schedule_class = scheduleClass
    self.service_class  = serviceClass
    self.direction      = direction
    self.block_id       = blockID

  def __str__(self):
    return "Run: %s heading %s at %s" % (self.route, self.direction, self.stops[0].time)

  def __repr__(self):
    return "Run(route=%s, stops=%s, scheduleClass=%s, serviceClass=%s, direction=%s, blockId=%s)" % \
        (self.route, list(map(repr, self.stops)), self.schedule_class, self.service_class, self.direction, self.block_id)


class Direction(object):
  """A direction of travel for a single route

  Parameters
  ----------
  route : str
      route identifier
  stops : [Stop]
  tag : str
      identifier for this direction
  title : str
      human-readable name for this direction
  name : str
  """
  def __init__(self, route, stops, tag, title, name, **kwargs):
    self.route = str(route)
    self.stops = stops
    self.tag   = str(tag)
    self.title = str(title)
    self.name  = str(name)

  def __str__(self):
    return "Direction: %s on %s" % (self.name, self.route)

  def __repr__(self):
    return "Direction(route=%s, stops=%s, tag=%s, title=%s, name=%s)" % \
        (self.route, [repr(stop) for stop in self.stops], self.tag, self.title, self.name)


class Stop(object):
  """A single bus stop

  Parameters
  ----------
  route : str
      route identifier
  tag : str
      identifier for this stop
  title : str
      human-readable name for this stop
  lat : float
  lon : float
  stopId : str
  shortTitle : str
      short human-readable name for this stop
  """
  def __init__(self, route, tag, title, lat, lon, stopId=None, shortTitle=None, **kwargs):
    self.route       = str(route)
    self.tag         = str(tag)
    self.title       = str(title)
    self.lat         = float(lat)
    self.lon         = float(lon)
    self.short_title = str(shortTitle or title)
    self.stop_id     = str(stopId)

  def __str__(self):
    return "Stop: %s on %s" % (self.title, self.tag)

  def __repr__(self):
    return "Stop(route=%s, tag=%s, title=%s, lat=%s, lon=%s, stopId=%s, title=%s)" % \
        (self.route, self.tag, self.title, self.lat, self.lon, self.stop_id, self.short_title)

