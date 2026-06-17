import hashlib


def generate_sha256_hash(file_path: str) -> str:
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as file:
        for block in iter(lambda: file.read(4096), b''):
            sha256.update(block)
    return sha256.hexdigest()
