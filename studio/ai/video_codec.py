"""Shared helper for opening a local OpenCV video writer with a real,
working codec, trying browser-playable H.264 first and falling back to
MPEG-4 — since not every host has an H.264 encoder available (e.g. Render's
Linux build image has neither the Windows OpenH264 DLL trick nor a system
libx264)."""
import cv2

CANDIDATE_FOURCCS = ['avc1', 'mp4v']


def open_writer(path, fps, size):
    """Returns an opened cv2.VideoWriter, or None if no codec works at all."""
    for fourcc_name in CANDIDATE_FOURCCS:
        fourcc = cv2.VideoWriter_fourcc(*fourcc_name)
        writer = cv2.VideoWriter(str(path), fourcc, fps, size)
        if writer.isOpened():
            return writer, fourcc_name
        writer.release()
    return None, None
