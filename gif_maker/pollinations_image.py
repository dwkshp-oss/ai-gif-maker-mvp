from __future__ import annotations

from io import BytesIO
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from PIL import Image

from gif_maker.config import AppConfig
from gif_maker.generator import GenerationRequest
from gif_maker.openai_image import FRAME_SIZE_BY_RATIO, build_image_prompt, make_animated_frames


class PollinationsImageGenerationError(RuntimeError):
    pass


class PollinationsFrameGenerator:
    def __init__(self, config: AppConfig):
        self.config = config

    @property
    def is_available(self) -> bool:
        return bool(self.config.pollinations_enabled)

    def generate_frames(self, request: GenerationRequest) -> list[Image.Image]:
        image = self._generate_image(request)
        return make_animated_frames(image, request.ratio)

    def _generate_image(self, request: GenerationRequest) -> Image.Image:
        url = build_pollinations_url(request, model=self.config.pollinations_model)
        http_request = Request(
            url,
            headers={
                "User-Agent": "AI-GIF-Maker-MVP/1.0",
                "Accept": "image/png,image/jpeg,image/webp,*/*",
            },
        )
        try:
            with urlopen(http_request, timeout=self.config.pollinations_timeout_seconds) as response:
                content_type = response.headers.get("Content-Type", "")
                data = response.read()
        except Exception as exc:
            raise PollinationsImageGenerationError(str(exc)) from exc

        if not content_type.startswith("image/"):
            raise PollinationsImageGenerationError(f"Pollinations returned non-image response: {content_type}")

        try:
            return Image.open(BytesIO(data)).convert("RGB")
        except Exception as exc:
            raise PollinationsImageGenerationError("Pollinations image response could not be decoded.") from exc


def build_pollinations_url(request: GenerationRequest, model: str = "flux") -> str:
    width, height = FRAME_SIZE_BY_RATIO[request.ratio]
    prompt = build_image_prompt(request)
    query = urlencode(
        {
            "width": width,
            "height": height,
            "model": model,
            "nologo": "true",
            "private": "true",
            "enhance": "false",
            "safe": "true",
        }
    )
    return f"https://image.pollinations.ai/prompt/{quote(prompt, safe='')}?{query}"
