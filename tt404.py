from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from  lxml import etree
import urllib2
import re
from itertools import ifilter
import json
import base64
from conf import libBlacklist, pluginBlacklist, noManage, noBrowse, plexOnlineOnly, viewerAge
import datetime
import contentRatings

kPluginShortPaths = ['/music', '/photos', '/video', '/applications']
kPluginPaths =  kPluginShortPaths + map(lambda x: x+'/', kPluginShortPaths)
kErrorBody = '<html><head><title>Not Found</title></head><body><h1>404 Not Found</h1></body></html>'
kForbiddenBody = '<html><head><title>Forbidden</title></head><body><h1>403 Forbidden</h1></body></html>'

# CHECK: Is there some way to access media using the part key?
# TODO: Have this work with other HTTP verbs: HEAD, PUT, TRACE, OPTIONS, CONNECT, PATCH
# TODO: Create conf for ipfw
# TODO: FIX crash when asking for /video_s_

def getURL(url, data, headers):
  print 'Requesting', url, data, headers
  headerDict = dict()
  for k, v in headers:
    headerDict[k] = v
    
  if not data: data = None
  req = urllib2.Request(url, data, headerDict, headerDict['host'])
  f = urllib2.urlopen(req)
  content = f.read()
  
  headerStr = str(f.headers)
  headers = dict()
  for headerLine in headerStr.split('\r\n')[:-1]:
    k, v = headerLine.split(':', 1)
    headers[k] = v[1:]
  return content, headers

def getEtree(url, data, headers):
  content, headers = getURL(url, data, headers)
  return etree.fromstring(content), headers

def getJSON(url, data=None, headers=None):
  content, headers = getURL(url, data, headers)
  return json.load(content), headers

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
  
class PMSHandler(BaseHTTPRequestHandler):
  def getDataAndHeaders(self):
    headers = self.headers.items()
    if 'Content-Length' in headers:
      varLen = int(headers['Content-Length'])
      data = s.rfile.read(varLen)
    else: data = None
    return data, headers

  def stripSections(self, path, itemType):
    out = ''
    itemCount = 0
    
    if itemType == 'lib': shouldStrip = lambda item:item.get('key') in libBlacklist
    elif itemType == 'libMenu': shouldStrip = lambda item: viewerAge and contentRatings.minAgeForContentRating(item.get('contentRating')) > viewerAge
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
    
    original, headers = getEtree('http://127.0.0.1:32400' + path, *self.getDataAndHeaders())
    for item in original.xpath('/MediaContainer/*'):
      if not shouldStrip(item):
        out += etree.tostring(item)
        itemCount += 1
    
    # Populate top level element
    outer = '<?xml version="1.0" encoding="UTF-8"?>\n<MediaContainer '
    for k,v in original.xpath('/MediaContainer')[0].attrib.iteritems():
      if k != 'size': outer += '%s="%s" ' % (k, v)
    outer += 'size="%i">\n' % itemCount
    return outer + out + '</MediaContainer>', headers
  
  def stripFolders(self, path):
    sections, headers = getEtree('http://127.0.0.1:32400/library/sections', *self.getDataAndHeaders())
    del headers
    folderBlacklist = list()
    for item in sections.xpath('/MediaContainer/Directory'):
      if item.get('key') in libBlacklist:
        for location in item.xpath('./Location'):
          folderBlacklist.append(location.get('path'))
    
    out = ''
    itemCount = 0
    content, headers = etree.parse('http://127.0.0.1:32400' + path, *self.getDataAndHeaders())
    for item in content.xpath('/MediaContainer/Path'):
      if item.get('path') not in folderBlacklist:
        out += etree.tostring(item)
        itemCount += 1
    return '<?xml version="1.0" encoding="UTF-8"?>\n<MediaContainer size="%i">\n' % itemCount + out + '</MediaContainer>', headers
  
  def handleRequest(self):
    err = forbid = passthrough = False

    if self.path == '/library/sections' or self.path == '/library/sections/':
      out, headers = self.stripSections(self.path, 'lib')
    elif self.path.startswith('/system/library/sections'):
      out, headers = self.stripSections(self.path, 'libSystem')
    elif self.path.startswith('/library/sections/'):
      if self.path.split('/')[3] in libBlacklist: err = True
      elif re.match(r'/library/sections/[^/]+/.+', self.path): out, headers = self.stripSections(self.path, 'libMenu')
      else: passthrough = True
    elif self.path in kPluginPaths:
      kind = 'pluginOnlineOnly' if plexOnlineOnly else 'plugin'
      out, headers = self.stripSections(self.path, kind)
    elif re.match(r'/system/plugins/[^/]+[/]?$', self.path):
      kind = 'pluginSystemOnlineOnly' if plexOnlineOnly else 'pluginSystem'
      out, headers = self.stripSections(self.path, kind)
    elif any(ifilter(lambda p: self.path.startswith(p), kPluginShortPaths)):
      pathComponents = self.path.split('/')
      if len(pathComponents) < 3:
        err = True
      else:
        pluginName = pathComponents[2]
        if plexOnlineOnly and pluginName in getNonPlexOnlinePlugins() or pluginName in pluginBlacklist:
          err = True
        else:
          passthrough = True
    elif self.path.startswith('/services/browse'):
      if noBrowse:
        forbid = True
      else:
        out, headers = self.stripFolders(self.path)
    elif noManage and self.path.startswith('/manage'):
      forbid = True
    elif re.match(r'/library/metadata/.+', self.path):
      out, headers = getEtree('http://127.0.0.1:32400' + self.path, *self.getDataAndHeaders())
      contentRating = out.xpath('/MediaContainer/*/@contentRating')
      if contentRating and viewerAge and contentRatings.minAgeForContentRating(contentRating[0]) > viewerAge:
        err = True
    else:
      passthrough = True
    
    if passthrough:
      out, headers = getURL('http://127.0.0.1:32400' + self.path, *self.getDataAndHeaders())
    
    if err:
      self.send_response(404, 'Not found')
      headers = {'Content-Type': 'text/html'}
      out = kErrorBody
    elif forbid:
      self.send_response(403, 'Forbidden')
      headers = {'Content-Type': 'text/html'}
      out = kForbiddenBody
    else:
      self.send_response(200)
    
    for k, v in headers.iteritems():
      if k != 'Content-Length': self.send_header(k, v)
      else: self.send_header('Content-Length', len(out))
    self.end_headers()
    
    self.wfile.write(out)

  def do_GET(self):
    self.handleRequest()
  
  def do_POST(self):
    self.handleRequest()


def main():
  BaseHTTPRequestHandler.address_string = _bare_address_string # see comment above
  print 'starting server'
  server = HTTPServer(('127.0.0.1', 32404), PMSHandler)
  print 'server started'
  if plexOnlineOnly: getNonPlexOnlinePlugins()
  try: server.serve_forever()
  except KeyboardInterrupt:
    print 'Shutting down'
    server.socket.close()

if __name__ == '__main__':
  main()

