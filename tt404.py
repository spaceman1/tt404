from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from  lxml import etree
import urllib

from conf import libBlacklist

def getURL(url):
  f = urllib.urlopen(url)
  r = f.read()
  f.close()
  return r

def _bare_address_string(self):
  # Thank you, thank you, thank you, Santoso Wijaya (santa4nt) http://bugs.python.org/issue6085
  host, port = self.client_address[:2]
  return '%s' % host

def stripSections(path, itemType):
  out = ''
  itemCount = 0
  shouldStrip = lambda item:item.get('key') in libBlacklist if (itemType == 'lib') else lambda item:item.get('identifier') in pluginBlacklist
  original = etree.parse('http://127.0.0.1:32400' + path)
  for item in original.xpath('/MediaContainer/Directory'):
    if not shouldStrip(item):
      out += etree.tostring(item)
      itemCount += 1
  
  # Populate top level element
  outer = '<MediaContainer '
  for k,v in original.xpath('/MediaContainer')[0].attrib.iteritems():
    if k != 'size': outer += '%s="%s" ' % (k, v)
  outer += 'size="%i">\n' % itemCount
  return outer + out + '</MediaContainer>'
  

class PMSHandler(BaseHTTPRequestHandler):
  def do_GET(self):
    print 'handling get request ' + self.path
    err = False
    if self.path == '/library/sections' or self.path == '/library/sections/':
      out = stripSections(self.path, 'lib')
    elif self.path.startswith('/library/sections/'):
      if self.path.split('/')[3] in libBlacklist:
        err = True
        out = '<html><head><title>Not Found</title></head><body><h1>404 Not Found</h1></body></html>'
      else:
        out = getURL('http://127.0.0.1:32400' + self.path)
    else:
      # TODO: copy headers from PMS
      print 'unknown path:' + self.path
      out = getURL('http://127.0.0.1:32400' + self.path)
    
    if err:
      self.send_response(404, 'Not found')
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

