from app.services.hashing import compute_sha256

def test_same_content_produces_same_hash():
    content = b"invoice data here for test"
    assert compute_sha256(content) == compute_sha256(content)

def test_different_content_produces_different_hash():
    assert compute_sha256(b"content 1") != compute_sha256(b"content 2")

def test_known_hash_value():
    # sha256 of empty bytes is a well-known constant — good sanity check the function isn't doing something odd
    assert compute_sha256(b"") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"