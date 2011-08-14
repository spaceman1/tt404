tt404
===============

Privacy/Content-Filtering firewall for Plex Media Server

Before you start
----------------
    easy_install lxml

Usage
-----
cd to the tt404 directory
    ./install
    ./tt404

The server is up and running but it doesn't do much yet.

Stop it by pressing ^C

See the list of library and plug-in identifiers with:
    ./lspms

Now edit conf.py in your favourite text editor

Restart the server
    ./tt404

Compatibility
-------------
Required: python and the lxml module.

Recommended: PF or ipfw. If you're running the media server on OS X you're already covered.

If your system does not include either of those firewalls: install a firewall that can handle redirection and configure it manually. Skip the ./install step.

Known Issues
------------
Plex for iOS seems to route around the firewall. More info as it becomes available.

This is an early beta. Plex is updated frequently. Some holes might still exist or be opened in future versions of Plex. If you find one please message me with details so I can plug it.
