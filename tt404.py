from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from  lxml import etree
import urllib
import re
from itertools import ifilter

from conf import libBlacklist, pluginBlacklist, noManage, noBrowse

kPluginShortPaths = ['/music', '/photos', '/video', '/applications']
kPluginPaths =  kPluginShortPaths + map(lambda x: x+'/', kPluginShortPaths)
kErrorBody = '<html><head><title>Not Found</title></head><body><h1>404 Not Found</h1></body></html>'
kForbiddenBody = '<html><head><title>Forbidden</title></head><body><h1>403 Forbidden</h1></body></html>'

# ignored sections: accounts, search, servers, status
# partially ignored: services, system
# sections TODO: /manage

# TODO: block attempts to access hidden plug-ins
# TODO: option to block all items from outside the app store
# TODO: Have this work with other HTTP verbs: HEAD, GET, POST, PUT, TRACE, OPTIONS, CONNECT, PATCH
# TODO: Add the pf.conf file, create one for ipfw, create an installer script
# TODO: Create a script for easy lookup of library+plug-in names+IDs
# TODO: Add a sample conf file
# TODO: Copy headers from PMS, overwrite only the content-length

# ISSUE: We can't block attempts to see inside hidden plug-ins without knowing their key. We can't filter /system/plugins/* that way as the keys are wonky
# POSSIBLE Solution: maintain a whitelist of valid keys based on calls to plugin directories

def getURL(url):
  f = urllib.urlopen(url)
  r = f.read()
  f.close()
  return r

def _bare_address_string(self):
  # Thank you, thank you, thank you, Santoso Wijaya (santa4nt) http://bugs.python.org/issue6085
  host, port = self.client_address[:2]
  return '%s' % host
  

class PMSHandler(BaseHTTPRequestHandler):
  def stripSections(self, path, itemType):
    out = ''
    itemCount = 0
    
    if itemType == 'lib': shouldStrip = lambda item:item.get('key') in libBlacklist
    elif itemType == 'plugin': shouldStrip = lambda item:item.get('identifier') in pluginBlacklist
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
    print 'handling get request ' + self.path
    err = False
    forbid = False
    if self.path == '/library/sections' or self.path == '/library/sections/':
      out = self.stripSections(self.path, 'lib')
    elif self.path.startswith('/library/sections/') and self.path.split('/')[3] in libBlacklist:
      err = True
      out = kErrorBody
    elif self.path in kPluginPaths or re.match(r'/system/plugins/[^/]+[/]?$', self.path):
      out = self.stripSections(self.path, 'plugin')
    elif any(ifilter(lambda p: self.path.startswith(p), kPluginShortPaths)) and self.path.split('/')[2] in pluginBlacklist:
      err = True
      out = kErrorBody
    elif self.path.startswith('/services/browse'):
      if noBrowse:
        forbid = True
        out = kForbiddenBody
      else:
        out = self.stripFolders(self.path)
        out = kForbiddenBody
    elif noManage and self.path.startswith('/manage'):
      forbid = True
      out = kForbiddenBody
    else:
      print 'unknown path:' + self.path
      out = getURL('http://127.0.0.1:32400' + self.path)
    
    if err:
      self.send_response(404, 'Not found')
      self.send_header('Content-type', 'text/html')
    elif forbid:
      self.send_response(403, 'Forbidden')
      self.send_header('Content-type', 'text/html')
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
  try: server.serve_forever()
  except KeyboardInterrupt:
    print 'Shutting down'
    server.socket.close()

if __name__ == '__main__':
  main()

