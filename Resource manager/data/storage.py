import json
from pathlib import Path

class LinkStorage:
    def __init__(self, file_path: str | None = None):
        base_dir = Path(__file__).resolve().parent.parent  # Resource manager/
        storage_dir = base_dir / "storage"
        storage_dir.mkdir(parents=True, exist_ok=True)

        self.file_path = Path(file_path) if file_path else (storage_dir / "links.json")
        if not self.file_path.exists():
            self.file_path.write_text("[]", encoding="utf-8")

        self.data = self.load()

    def load(self):
        try:
            if not self.file_path.exists():
                return []
            raw = self.file_path.read_text(encoding="utf-8").strip()
            if not raw:
                return []
            data = json.loads(raw)
            return data if isinstance(data, list) else []
        except json.JSONDecodeError:
            return []
        except OSError:
            return []

    def save(self):
        tmp = self.file_path.with_suffix(self.file_path.suffix + ".tmp")
        tmp.write_text(json.dumps(self.data, indent=4, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.file_path)

    def add_link(self, title, url):
        self.data.append({"title": title, "url": url})
        self.save()

    def remove_link(self, index):
        if 0 <= index < len(self.data):
            del self.data[index]
            self.save()