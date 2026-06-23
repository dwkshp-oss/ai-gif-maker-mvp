from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


@dataclass(frozen=True)
class AppConfig:
    generated_dir: Path
    download_dir: Path
    host: str = "127.0.0.1"
    port: int = 5000
    debug: bool = False
    default_style: str = "cute3d"
    default_ratio: str = "9:16"
    gif_duration_seconds: int = 3
    frame_duration_ms: int = 120
    rate_limit_count: int = 10
    rate_limit_window_seconds: int = 60
    openai_api_key: str = ""
    openai_image_model: str = "gpt-image-2"
    openai_image_quality: str = "low"
    openai_image_enabled: bool = False
    pollinations_enabled: bool = True
    pollinations_model: str = "flux"
    pollinations_timeout_seconds: int = 90
    download_to_server_enabled: bool = False

    @classmethod
    def from_env(cls) -> "AppConfig":
        load_dotenv()
        project_root = Path(__file__).resolve().parents[1]
        user_home = Path(os.getenv("USERPROFILE") or Path.home())
        return cls(
            generated_dir=Path(os.getenv("GENERATED_DIR", project_root / "generated")),
            download_dir=Path(os.getenv("DOWNLOAD_DIR", user_home / "Downloads" / "AI_GIF_Maker")),
            host=os.getenv("FLASK_RUN_HOST", "127.0.0.1"),
            port=int(os.getenv("PORT", "5000")),
            debug=os.getenv("FLASK_DEBUG", "0").lower() in {"1", "true", "yes"},
            default_style=os.getenv("DEFAULT_STYLE", "cute3d"),
            default_ratio=os.getenv("DEFAULT_RATIO", "9:16"),
            gif_duration_seconds=int(os.getenv("GIF_DURATION_SECONDS", "3")),
            frame_duration_ms=int(os.getenv("FRAME_DURATION_MS", "120")),
            rate_limit_count=int(os.getenv("RATE_LIMIT_COUNT", "10")),
            rate_limit_window_seconds=int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60")),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            openai_image_model=os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-2"),
            openai_image_quality=os.getenv("OPENAI_IMAGE_QUALITY", "low"),
            openai_image_enabled=os.getenv("OPENAI_IMAGE_ENABLED", "0").lower() in {"1", "true", "yes"},
            pollinations_enabled=os.getenv("POLLINATIONS_ENABLED", "1").lower() in {"1", "true", "yes"},
            pollinations_model=os.getenv("POLLINATIONS_MODEL", "flux"),
            pollinations_timeout_seconds=int(os.getenv("POLLINATIONS_TIMEOUT_SECONDS", "90")),
            download_to_server_enabled=os.getenv("DOWNLOAD_TO_SERVER_ENABLED", "0").lower() in {"1", "true", "yes"},
        )
