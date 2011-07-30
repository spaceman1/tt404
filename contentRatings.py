_contentRatingMinAges = {
'C': 2, 'C8':8, '14+': 14, '18+': 18, '21': 21, 'X': 21, 'E':0, 'G':0, '14A': 14, '18A': 18, 'R': 17, 'A': 18, # Canada
'G': 0, '8+': 8, '13+': 13, '16+': 16, '18+': 18, # Quebec TV
'PG': 10, 'PG-13': 13, 'R': 17, 'NC-17': 17, 'TV-Y': 0, 'TV-Y7': 7, 'TV-Y7-FV': 7, 'TV-G': 0, 'TV-PG': 10, 'TV-14': 14, 'TV-MA': 17, # United States
'XXX': 18 # Not that it's used in any of the current agents
}

# Note: Adult accompaniment is assumed. "Shared Responsibility" isn't

def minAgeForContentRating(contentRating):
  if not contentRating: return 0
  minAge = _contentRatingMinAges.get(contentRating)
  if contentRating == None: print 'Unknown content rating ' + str(contentRating)
  return minAge