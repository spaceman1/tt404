import re

_contentRatingMinAges = {
'C': 2, 'X': 21, 'E':0, 'G':0, 'R': 17, 'A': 18, # Canada
'G': 0, # Quebec TV
'PG': 10, 'PG-13': 13, 'R': 17, 'TV-Y': 0, 'TV-G': 0, 'TV-PG': 10, 'TV-MA': 17, # United States
'XXX': 18 # Not that it's used in any of the current agents
}
# Note: Adult accompaniment is assumed. "Shared Responsibility" isn't

# TODO: scrape http://en.wikipedia.org/wiki/Motion_picture_rating_system#Comparison
# the Edit section provides a parseable format 

def minAgeForContentRating(contentRating):
  if not contentRating: return 0
  match = re.search(r'(\d+)', contentRating)
  if match: return int(match.group(1))
  
  minAge = _contentRatingMinAges.get(contentRating)
  if contentRating == None: print 'Unknown content rating ' + str(contentRating)
  return minAge