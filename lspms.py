#!/usr/bin/python
from lxml import etree
import urllib
from conf import libBlacklist, pluginBlacklist

# TODO: have this list items that are hidden by plexOnlineOnly

print 'Libraries'
print 'Hidden ID   Name'
print '----------------------------------'
for item in etree.parse(urllib.urlopen('http://127.0.0.1:32400/library/sections')).xpath('/MediaContainer/Directory'):
  key = item.get('key')
  hidden = 'Yes' if key in libBlacklist else '   '
  print '%s   %2s   %s' %(hidden, key, item.get('title'))

print '\n\nPlug-ins'
print 'Hidden ID' + 41 * ' ' + 'Name'
print '-' * 61
for item in etree.parse(urllib.urlopen('http://127.0.0.1:32400/system/plugins/all')).xpath('/MediaContainer/Directory'):
  key = item.get('identifier')
  hidden = 'Yes' if key in pluginBlacklist else '   '
  print '%s   %40s   %s' %(hidden, key, item.get('title'))
