# angelstudios-kodi
Angel Studios KODI Addon

Initial commit from basic testing code.

For each revision, update the `version.txt` file.  The `addon.xml` will be updated
to match when you run the `build.sh` script.

# For development environment
linking in Linux

# TODO
* Implement correct behavior for unauthenticated users.
  * Most shows should not be viewable without authentication, to match the
  behavoir of the website.  Some limited trailers and previews _are_ available
  without authentication.  Unsure how to identify these.  May have to pull
  the episode page and parse for the login bits.
* Handle bad username/password errors.