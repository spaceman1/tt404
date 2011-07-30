from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from  lxml import etree
import urllib
import re
from itertools import ifilter
import json
import base64
from conf import libBlacklist, pluginBlacklist, noManage, noBrowse, plexOnlineOnly
import datetime

kPluginShortPaths = ['/music', '/photos', '/video', '/applications']
kPluginPaths =  kPluginShortPaths + map(lambda x: x+'/', kPluginShortPaths)
kErrorBody = '<html><head><title>Not Found</title></head><body><h1>404 Not Found</h1></body></html>'
kForbiddenBody = '<html><head><title>Forbidden</title></head><body><h1>403 Forbidden</h1></body></html>'

# CHECK: Is there some way to access media using the part key?
# TODO: Have this work with other HTTP verbs: HEAD, GET, POST, PUT, TRACE, OPTIONS, CONNECT, PATCH
# TODO: Create conf for ipfw
# TODO: Copy headers from PMS, overwrite only the content-length
# TODO: FIX crash when asking for /video_s_

def getURL(url):
  f = urllib.urlopen(url)
  r = f.read()
  f.close()
  return r

def _bare_address_string(self):
  # Thank you, thank you, thank you, Santoso Wijaya (santa4nt) http://bugs.python.org/issue6085
  host, port = self.client_address[:2]
  return '%s' % host

_nonPlexOnlinePlugins = list()
_nonPlexOnlinePluginsCacheTime = datetime.datetime(datetime.MINYEAR, 1, 1)
def getNonPlexOnlinePlugins():
  global _nonPlexOnlinePlugins, _nonPlexOnlinePluginsCacheTime
  elapsed = datetime.datetime.now() - _nonPlexOnlinePluginsCacheTime
  if elapsed.total_seconds() < 3600: return _nonPlexOnlinePlugins
  print 'Getting online plug-ins'
  identifiers = list()
  for item in json.load(urllib.urlopen('http://plugins.plexapp.com/apps/all.json')):
    identifiers.append(item['app']['identifier'])
  plugins = list()
  for item in etree.parse('http://127.0.0.1:32400/system/plugins/all').xpath('/MediaContainer/Directory'):
    if item.get('identifier') not in identifiers: plugins.append(base64.b64decode(item.get('key') + '==').split('/')[-1])
  _nonPlexOnlinePlugins = plugins
  _nonPlexOnlinePluginsCacheTime = datetime.datetime.now()
  return plugins

_metadataKeys = dict()
_metadataKeysCacheTime = datetime.datetime(datetime.MINYEAR, 1, 1)
def validateMetadataKey(key):
  global _metadataKeys, _metadataKeysCacheTime
  try: return _metadataKeys[key]
  except KeyError: pass
  elapsed = datetime.datetime.now() - _metadataKeysCacheTime
  if elapsed.total_seconds() < 3600: raise KeyError
  print 'Getting metadata keys'
  base = 'http://127.0.0.1:32400/library/sections/'
  for lib in etree.parse(base).xpath('/MediaContainer/Directory'):
    v = lib.get('key') not in libBlacklist
    for item in etree.parse(base + lib.get('key') + '/all').xpath('/MediaContainer/Video/@ratingKey'):
      _metadataKeys[item] = v
  _metadataKeysCacheTime = datetime.datetime.now()
  return _metadataKeys[key]
  
class PMSHandler(BaseHTTPRequestHandler):
  def stripSections(self, path, itemType):
    out = ''
    itemCount = 0
    
    if itemType == 'lib': shouldStrip = lambda item:item.get('key') in libBlacklist
    elif itemType == 'libSystem': shouldStrip = lambda item:base64.b64decode(item.get('key') + '==').split('/')[-1] in libBlacklist
    elif itemType == 'plugin': shouldStrip = lambda item:item.get('key') in pluginBlacklist
    elif itemType == 'pluginSystem': shouldStrip = lambda item:base64.b64decode(item.get('key') + '==').split('/')[-1] in pluginBlacklist
    elif itemType == 'pluginOnlineOnly':
      combinedBlacklist = getNonPlexOnlinePlugins() + pluginBlacklist
      shouldStrip = lambda item:item.get('key') in combinedBlacklist
    elif itemType == 'pluginSystemOnlineOnly':
      combinedBlacklist = getNonPlexOnlinePlugins() + pluginBlacklist
      shouldStrip = lambda item: base64.b64decode(item.get('key') + '==').split('/')[-1] in combinedBlacklist
    else:
      print 'unknown item type ' + itemType
      shouldStrip = lambda item:False
    
    original = etree.parse('http://127.0.0.1:32400' + path)
    for item in original.xpath('/MediaContainer/Directory'):
      if not shouldStrip(item):
        out += etree.tostring(item)
        itemCount += 1
    
    # Populate top level element
    outer = '<?xml version="1.0" encoding="UTF-8"?>\n<MediaContainer '
    for k,v in original.xpath('/MediaContainer')[0].attrib.iteritems():
      if k != 'size': outer += '%s="%s" ' % (k, v)
    outer += 'size="%i">\n' % itemCount
    return outer + out + '</MediaContainer>'
  
  def stripFolders(self, path):
    sections = etree.parse('http://127.0.0.1:32400/library/sections')
    folderBlacklist = list()
    for item in sections.xpath('/MediaContainer/Directory'):
      if item.get('key') in libBlacklist:
        for location in item.xpath('./Location'):
          folderBlacklist.append(location.get('path'))
    
    out = ''
    itemCount = 0
    for item in etree.parse('http://127.0.0.1:32400' + path).xpath('/MediaContainer/Path'):
      if item.get('path') not in folderBlacklist:
        out += etree.tostring(item)
        itemCount += 1
    return '<?xml version="1.0" encoding="UTF-8"?>\n<MediaContainer size="%i">\n' % itemCount + out + '</MediaContainer>'
  
  def do_GET(self):
    err = forbid = passthrough = False
    
    if self.path == '/library/sections' or self.path == '/library/sections/':
      out = self.stripSections(self.path, 'lib')
    elif self.path.startswith('/system/library/sections'):
      out = self.stripSections(self.path, 'libSystem')
    elif self.path.startswith('/library/sections/') and self.path.split('/')[3] in libBlacklist:
      err = True
    elif self.path in kPluginPaths:
      kind = 'pluginOnlineOnly' if plexOnlineOnly else 'plugin'
      out = self.stripSections(self.path, kind)
    elif re.match(r'/system/plugins/[^/]+[/]?$', self.path):
      kind = 'pluginSystemOnlineOnly' if plexOnlineOnly else 'pluginSystem'
      out = self.stripSections(self.path, kind)
    elif any(ifilter(lambda p: self.path.startswith(p), kPluginShortPaths)):
      pluginName = self.path.split('/')[2]
      if plexOnlineOnly and pluginName in getNonPlexOnlinePlugins() or pluginName in pluginBlacklist:
        err = True
      else:
        passthrough = True
    elif self.path.startswith('/services/browse'):
      if noBrowse:
        forbid = True
      else:
        out = self.stripFolders(self.path)
    elif noManage and self.path.startswith('/manage'):
      forbid = True
    elif re.match(r'/library/metadata/.+', self.path):
      try: v = validateMetadataKey(self.path.split('/')[-1])
      except KeyError: err = True
      else:
        if not v: err = True
        else: passthrough = True
    else:
      passthrough = True
    
    if passthrough:
      print 'unknown path:' + self.path
      out = getURL('http://127.0.0.1:32400' + self.path)
    
    if err:
      self.send_response(404, 'Not found')
      self.send_header('Content-type', 'text/html')
      out = kErrorBody
    elif forbid:
      self.send_response(403, 'Forbidden')
      self.send_header('Content-type', 'text/html')
      out = kForbiddenBody
    else:
      self.send_response(200)
      self.send_header('Content-type', 'text/xml;charset=utf-8')
    
    self.send_header('Content-length', len(out))
    self.send_header('X-Plex-Protocol', '1.0')
    self.end_headers()
    self.wfile.write(out)
  
#  def do_POST(self):


def main():
  BaseHTTPRequestHandler.address_string = _bare_address_string # see comment above
  print 'starting server'
  server = HTTPServer(('', 32404), PMSHandler)
  print 'server started'
  if plexOnlineOnly: getNonPlexOnlinePlugins()
  try: server.serve_forever()
  except KeyboardInterrupt:
    print 'Shutting down'
    server.socket.close()

if __name__ == '__main__':
  main()

