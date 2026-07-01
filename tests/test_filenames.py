from translatedub.filenames import sanitize_stem, unique_path


def test_sanitize_stem_basic():
    assert sanitize_stem("My Video.mp4") == "My Video"


def test_sanitize_stem_preserves_unicode():
    assert sanitize_stem("Bài học.mp4") == "Bài học"


def test_sanitize_stem_strips_unsafe():
    # basename drops the directory part, then unsafe chars collapse to underscores
    assert sanitize_stem("dir/b:c*?.mov") == "b_c"


def test_sanitize_stem_empty_falls_back():
    assert sanitize_stem("") == "video"
    assert sanitize_stem("   .mp4") == "video"


def test_sanitize_stem_length_cap():
    assert len(sanitize_stem("x" * 200 + ".mp4")) == 90


def test_unique_path_no_collision(tmp_path):
    assert unique_path(str(tmp_path), "a.mp4") == str(tmp_path / "a.mp4")


def test_unique_path_with_collision(tmp_path):
    (tmp_path / "a.mp4").write_text("x")
    assert unique_path(str(tmp_path), "a.mp4") == str(tmp_path / "a_2.mp4")
    (tmp_path / "a_2.mp4").write_text("x")
    assert unique_path(str(tmp_path), "a.mp4") == str(tmp_path / "a_3.mp4")
