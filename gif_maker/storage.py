from pathlib import Path
import shutil
import uuid

from PIL import Image
from werkzeug.utils import secure_filename


class LocalGifStorage:
    def __init__(self, output_dir: Path, download_dir: Path):
        self.output_dir = Path(output_dir).resolve()
        self.download_dir = Path(download_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save_gif(self, frames: list[Image.Image], duration_ms: int) -> str:
        if not frames:
            raise ValueError("저장할 프레임이 없습니다.")
        filename = f"{uuid.uuid4().hex}.gif"
        out_path = self.output_dir / filename
        frames[0].save(
            out_path,
            save_all=True,
            append_images=frames[1:],
            duration=duration_ms,
            loop=0,
            optimize=True,
        )
        return filename

    def public_url(self, filename: str) -> str:
        return f"/generated/{filename}"

    def path_for(self, filename: str) -> Path:
        safe_name = secure_filename(filename)
        if safe_name != filename or not safe_name.endswith(".gif"):
            raise FileNotFoundError("잘못된 파일명입니다.")
        path = (self.output_dir / safe_name).resolve()
        if self.output_dir not in path.parents or not path.exists():
            raise FileNotFoundError("GIF 파일을 찾을 수 없습니다.")
        return path

    def copy_to_downloads(self, filename: str) -> Path:
        source = self.path_for(filename)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        target = self.download_dir / source.name
        shutil.copy2(source, target)
        return target
