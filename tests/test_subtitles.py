import pytest

from translatedub.core.subtitles import (
    Subtitle,
    ms_to_srt_time,
    reindex,
    srt_time_to_ms,
    write_srt,
)


@pytest.mark.parametrize(
    "ms,expected",
    [
        (0, "00:00:00,000"),
        (1, "00:00:00,001"),
        (1000, "00:00:01,000"),
        (61_001, "00:01:01,001"),
        (3_661_042, "01:01:01,042"),
        (-5, "00:00:00,000"),  # clamps negatives
    ],
)
def test_ms_to_srt_time(ms, expected):
    assert ms_to_srt_time(ms) == expected


@pytest.mark.parametrize("srt,ms", [
    ("00:00:00,000", 0),
    ("01:01:01,042", 3_661_042),
    ("00:00:01.500", 1500),  # dot separator accepted
])
def test_srt_time_to_ms(srt, ms):
    assert srt_time_to_ms(srt) == ms


def test_srt_time_to_ms_bad_input():
    assert srt_time_to_ms("not a time") == 0


@pytest.mark.parametrize("ms", [0, 500, 60_000, 3_599_999, 7_384_120])
def test_srt_time_roundtrip(ms):
    assert srt_time_to_ms(ms_to_srt_time(ms)) == ms


def test_subtitle_duration_and_dicts():
    sub = Subtitle(index=1, start_ms=1000, end_ms=2500,
                   original_text=" hi ", translated_text=" chào ")
    assert sub.duration_ms == 1500
    round_tripped = Subtitle.from_dict(sub.to_dict())
    assert round_tripped.start_ms == 1000
    assert round_tripped.translated_text == "chào"
    assert "audio_path" not in sub.to_dict()


def test_subtitle_duration_never_negative():
    assert Subtitle(1, 3000, 1000).duration_ms == 0


def test_reindex():
    subs = [Subtitle(9, 0, 1), Subtitle(4, 1, 2), Subtitle(7, 2, 3)]
    reindex(subs)
    assert [s.index for s in subs] == [1, 2, 3]


def test_write_srt(tmp_path):
    subs = [
        Subtitle(1, 0, 1000, "hello", "xin chào"),
        Subtitle(2, 1000, 2000, "world", "thế giới"),
    ]
    out = tmp_path / "out.srt"
    write_srt(subs, str(out))
    text = out.read_text(encoding="utf-8")
    assert "1\n00:00:00,000 --> 00:00:01,000\nxin chào\n\n" in text
    assert "2\n00:00:01,000 --> 00:00:02,000\nthế giới\n\n" in text
