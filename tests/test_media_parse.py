from translatedub.core import media

SAMPLE_FFMPEG_STDERR = """\
Input #0, mov,mp4,m4a,3gp,3g2,mj2, from 'x.mp4':
  Duration: 00:01:03.45, start: 0.000000, bitrate: 1200 kb/s
  Stream #0:0(und): Video: h264 (High), yuv420p, 1280x720, 1000 kb/s
  Stream #0:1(und): Audio: aac (LC), 44100 Hz, stereo, fltp, 128 kb/s
"""


def test_duration_from_stderr():
    assert media._duration_from_ffmpeg_stderr(SAMPLE_FFMPEG_STDERR) == 63.45


def test_duration_from_stderr_no_match():
    assert media._duration_from_ffmpeg_stderr("no duration here") == 0.0


def test_get_duration_uses_ffprobe(monkeypatch):
    monkeypatch.setattr(media, "ffprobe_path", lambda: "/usr/bin/ffprobe")

    class R:
        stdout = "12.5\n"
    monkeypatch.setattr(media, "_run", lambda cmd, log=None: R())
    assert media.get_duration("x.mp4") == 12.5


def test_get_duration_falls_back_to_ffmpeg(monkeypatch):
    monkeypatch.setattr(media, "ffprobe_path", lambda: None)
    monkeypatch.setattr(media, "ffmpeg_path", lambda: "/usr/bin/ffmpeg")

    class R:
        stdout = ""
        stderr = SAMPLE_FFMPEG_STDERR
    monkeypatch.setattr(media, "_run", lambda cmd, log=None: R())
    assert media.get_duration("x.mp4") == 63.45


def test_has_audio_stream_ffmpeg_fallback(monkeypatch):
    monkeypatch.setattr(media, "ffprobe_path", lambda: None)
    monkeypatch.setattr(media, "ffmpeg_path", lambda: "/usr/bin/ffmpeg")

    class R:
        stdout = ""
        stderr = SAMPLE_FFMPEG_STDERR
    monkeypatch.setattr(media, "_run", lambda cmd, log=None: R())
    assert media.has_audio_stream("x.mp4") is True


def test_has_no_audio_stream(monkeypatch):
    monkeypatch.setattr(media, "ffprobe_path", lambda: None)
    monkeypatch.setattr(media, "ffmpeg_path", lambda: "/usr/bin/ffmpeg")

    class R:
        stdout = ""
        stderr = "Stream #0:0: Video: h264\n"
    monkeypatch.setattr(media, "_run", lambda cmd, log=None: R())
    assert media.has_audio_stream("x.mp4") is False
