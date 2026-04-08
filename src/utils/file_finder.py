import os

def find_file_in_assets(filename, start_dir="assets"):
    """Ищет файл во всех подпапках assets. Возвращает путь или None."""
    for root, dirs, files in os.walk(start_dir):
        if filename in files:
            return os.path.join(root, filename)
    return None