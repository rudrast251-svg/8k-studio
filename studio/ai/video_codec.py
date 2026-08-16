"""Shared helper for opening a local OpenCV video writer with a real,
browser-playable codec (H.264 only).

MPEG-4 ('mp4v') used to be tried as a fallback here, but it was a false
economy: cv2 happily writes it and reports success, yet Chrome (and most
browsers) refuse to play it at all (MEDIA_ERR_SRC_NOT_SUPPORTED) — so any
caller that treated a successful write as "it works" was silently shipping
broken video to users. Better to fail loudly so callers can degrade to
something that actually works (e.g. an image, or a clear error) than to
"succeed" at producing a file nobody can watch.
"""
import cv2

CANDIDATE_FOURCCS = ['avc1']


def open_writer(path, fps, size):
    """Returns an opened cv2.VideoWriter using a browser-playable codec, or
    None if no such codec is available on this host (e.g. Render's Linux
    build image, which has no H.264 encoder)."""
    for fourcc_name in CANDIDATE_FOURCCS:
        fourcc = cv2.VideoWriter_fourcc(*fourcc_name)
        writer = cv2.VideoWriter(str(path), fourcc, fps, size)
        if writer.isOpened():
            return writer, fourcc_name
        writer.release()
    return None, None
