import json

from extensions.supervisor_updates.collector import compute_hash, detect_changes, update_hashes


def test_compute_hash_is_deterministic():
    text = "Prof. Smith is hiring postdocs in medical imaging."
    assert compute_hash(text) == compute_hash(text)


def test_compute_hash_differs_for_different_text():
    h1 = compute_hash("We have an open postdoc position in CV.")
    h2 = compute_hash("No positions available at this time.")
    assert h1 != h2


def test_detect_changes_new_url(tmp_path):
    hashes_file = tmp_path / "supervisor_hashes.json"
    hashes_file.write_text("{}")
    changed = detect_changes(
        url="https://example.com/lab",
        current_text="We are hiring a postdoc in AI.",
        hashes_path=str(hashes_file),
    )
    assert changed is True


def test_detect_changes_same_content(tmp_path):
    text = "No current openings."
    h = compute_hash(text)
    hashes_file = tmp_path / "supervisor_hashes.json"
    hashes_file.write_text(json.dumps({"https://example.com/lab": h}))
    changed = detect_changes(
        url="https://example.com/lab",
        current_text=text,
        hashes_path=str(hashes_file),
    )
    assert changed is False


def test_update_hashes_persists(tmp_path):
    hashes_file = tmp_path / "supervisor_hashes.json"
    hashes_file.write_text("{}")
    update_hashes("https://example.com", "new content", str(hashes_file))
    stored = json.loads(hashes_file.read_text())
    assert "https://example.com" in stored
