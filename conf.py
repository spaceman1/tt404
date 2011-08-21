# The list of library sections to hide
libBlacklist = ['some id', 'some other id']

# The list of plug-ins to hide
pluginBlacklist = ['some id', 'some other id']

# Completely block the web manager
noManage = False

# Completely block filesystem browsing through /services/browse
noBrowse = False

# Block all plug-ins that aren't listed on plex online. You can still block additional plug-ins with pluginBlacklist
plexOnlineOnly = False

# Set the age of the viewer when filtering libraries. Set to 0 to disable.
viewerAge = 0

# Plug-in Preferences settings
# The values correspond to: read write
# Read: Users can see the value you've set the preference to
# Write: Users can set a new value

prefsAccess = {
	'read': True,
	'write': True
}

securePrefsAccess = {
	'read': True,
	'write': False
}

# Make the preferences completely stealth. (No info on which plug-ins have prefs, no way to list their prefs, @future: removal of prefs items from MediaContainers)
# True will override all other prefs settings
noPrefs = False