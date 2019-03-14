#distrib_ntua_2019
#noobcash
## The repository for the semester project for Distributed Systems 2019 NTUA

### Configuration (e.g. difficulty and capacity)
- Defaults are defined in `noobcash/__init__.py`
- `instance/config.py` overrides them (stays out of source control)
- The contents of the file pointed to by the NOOBCASH_SETTINGS environment variable (if set) overrides all of the above

### Settings (e.g. FLASK_APP, only applicable if using `flask run`)
- Defaults in `.flaskenv`
- `.env` overrides them (stays out of source control)
- environment variables override all of the above
