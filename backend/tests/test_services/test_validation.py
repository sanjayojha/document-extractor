
from app.services.validation import validate_file_size

def test_validate_file_size_accepts_normal_size():
    validate_file_size(1024)