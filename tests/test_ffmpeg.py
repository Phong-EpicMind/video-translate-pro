from translatedub import ffmpeg


def test_env_override(monkeypatch):
    ffmpeg.reset_cache()
    monkeypatch.setenv("TRANSLATEDUB_FFMPEG", "/custom/ffmpeg")
    assert ffmpeg.ffmpeg_path() == "/custom/ffmpeg"
    ffmpeg.reset_cache()


def test_ffprobe_env_override(monkeypatch):
    ffmpeg.reset_cache()
    monkeypatch.setenv("TRANSLATEDUB_FFPROBE", "/custom/ffprobe")
    assert ffmpeg.ffprobe_path() == "/custom/ffprobe"
    ffmpeg.reset_cache()


def test_ffmpeg_from_path(monkeypatch):
    ffmpeg.reset_cache()
    monkeypatch.delenv("TRANSLATEDUB_FFMPEG", raising=False)
    monkeypatch.setattr(ffmpeg.shutil, "which", lambda name: "/usr/bin/ffmpeg")
    assert ffmpeg.ffmpeg_path() == "/usr/bin/ffmpeg"
    ffmpeg.reset_cache()


def test_ffprobe_absent_returns_none(monkeypatch):
    ffmpeg.reset_cache()
    monkeypatch.delenv("TRANSLATEDUB_FFPROBE", raising=False)
    monkeypatch.setattr(ffmpeg.shutil, "which", lambda name: None)
    monkeypatch.setattr(ffmpeg, "_from_common_dirs", lambda name: None)
    assert ffmpeg.ffprobe_path() is None
    ffmpeg.reset_cache()
