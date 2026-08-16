import os
import sys

from django.apps import AppConfig
from django.conf import settings


class StudioConfig(AppConfig):
    name = 'studio'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        # On Windows, make the bundled OpenH264 codec discoverable so OpenCV's
        # ffmpeg backend can write real, browser-playable H.264 video for the
        # local demo-mode processing pipeline.
        if sys.platform == 'win32':
            bin_dir = str(settings.BASE_DIR / 'bin')
            if os.path.isdir(bin_dir):
                try:
                    os.add_dll_directory(bin_dir)
                except (AttributeError, OSError):
                    pass
                os.environ['PATH'] = bin_dir + os.pathsep + os.environ.get('PATH', '')
