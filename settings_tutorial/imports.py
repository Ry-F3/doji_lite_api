from pathlib import Path
import os
import dj_database_url

if os.path.exists('env.py'):
    import env