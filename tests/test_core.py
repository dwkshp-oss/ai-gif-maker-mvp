import tempfile
import unittest
from pathlib import Path

from PIL import Image

from app import create_app
from gif_maker.config import AppConfig
from gif_maker.generator import build_generation_request
from gif_maker.moderation import ModerationError, validate_prompt
from gif_maker.openai_image import (
    build_image_prompt,
    extract_scene_hints,
    make_animated_frames,
    normalize_prompt_for_image_model,
)
from gif_maker.pollinations_image import build_pollinations_url
from gif_maker.rate_limit import InMemoryRateLimiter


class CoreTests(unittest.TestCase):
    def test_request_validation(self):
        request = build_generation_request("product intro", "business", "9:16")
        self.assertEqual(request.style, "business")

    def test_prompt_moderation(self):
        with self.assertRaises(ModerationError):
            validate_prompt("explicit scene")

    def test_rate_limit(self):
        limiter = InMemoryRateLimiter(1, 60)
        self.assertTrue(limiter.allow("local"))
        self.assertFalse(limiter.allow("local"))

    def test_generate_and_save_to_downloads_with_local_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            app = create_app(
                AppConfig(
                    generated_dir=base / "generated",
                    download_dir=base / "downloads",
                    rate_limit_count=100,
                    pollinations_enabled=False,
                    openai_image_enabled=False,
                    download_to_server_enabled=True,
                )
            )
            client = app.test_client()
            response = client.post(
                "/api/generate",
                json={"prompt": "download test", "style": "cute3d", "ratio": "9:16"},
            )
            data = response.get_json()
            self.assertEqual(response.status_code, 200)
            self.assertTrue(data["ok"])
            self.assertEqual(data["metadata"]["provider"], "local-pillow-demo")
            self.assertIn("/view/", data["viewUrl"])

            save_response = client.post("/api/save-to-downloads", json={"filename": data["filename"]})
            save_data = save_response.get_json()
            self.assertEqual(save_response.status_code, 200)
            self.assertTrue(Path(save_data["path"]).exists())

            view_response = client.get(data["viewUrl"])
            self.assertEqual(view_response.status_code, 200)
            self.assertIn("GIF 다운로드", view_response.get_data(as_text=True))

    def test_generate_rejects_korean_prompt_in_english_only_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            app = create_app(
                AppConfig(
                    generated_dir=base / "generated",
                    download_dir=base / "downloads",
                    pollinations_enabled=False,
                    openai_image_enabled=False,
                )
            )
            client = app.test_client()
            response = client.post(
                "/api/generate",
                json={"prompt": "벚꽃이 휘날리는 GIF", "style": "cute3d", "ratio": "9:16"},
            )
            data = response.get_json()
            self.assertEqual(response.status_code, 400)
            self.assertFalse(data["ok"])
            self.assertEqual(data["error"], "ENGLISH_ONLY")

    def test_translate_prompt_endpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            app = create_app(
                AppConfig(
                    generated_dir=base / "generated",
                    download_dir=base / "downloads",
                    pollinations_enabled=False,
                    openai_image_enabled=False,
                )
            )
            client = app.test_client()
            response = client.post("/api/translate-prompt", json={"prompt": "귀여운 거북이가 춤추는 GIF"})
            data = response.get_json()
            self.assertEqual(response.status_code, 200)
            self.assertTrue(data["ok"])
            self.assertIn("cute turtle", data["englishPrompt"])

    def test_image_prompt_and_frame_animation(self):
        request = build_generation_request("coffee cup with a sparkling idea", "cute3d", "9:16")
        prompt = build_image_prompt(request)
        self.assertIn("coffee", prompt)
        self.assertIn("glowing idea light", prompt)
        self.assertIn("no watermark", prompt)

        image = Image.new("RGB", (1024, 1536), (255, 240, 200))
        frames = make_animated_frames(image, "9:16", frame_count=4)
        self.assertEqual(len(frames), 4)
        self.assertEqual(frames[0].size, (576, 1024))

    def test_pollinations_url(self):
        request = build_generation_request("coffee cup with a sparkling idea", "cute3d", "9:16")
        url = build_pollinations_url(request, model="flux")
        self.assertTrue(url.startswith("https://image.pollinations.ai/prompt/"))
        self.assertIn("width=576", url)
        self.assertIn("height=1024", url)
        self.assertIn("model=flux", url)
        self.assertIn("nologo=true", url)
        self.assertIn("enhance=false", url)

    def test_korean_scene_hints(self):
        hints = extract_scene_hints("커피잔 위로 반짝이는 아이디어가 떠오르는 GIF")
        self.assertIn("a clearly visible coffee cup", hints)
        self.assertIn("a glowing idea light above the main subject", hints)
        self.assertIn("sparkling light particles", hints)

    def test_korean_prompt_normalization(self):
        normalized = normalize_prompt_for_image_model("커피잔 위로 반짝이는 아이디어가 떠오르는 귀여운 3D GIF")
        self.assertIn("coffee cup", normalized)
        self.assertIn("glowing idea light bulb", normalized)
        self.assertIn("sparkling light particles", normalized)
        self.assertIn("soft 3D rendered style", normalized)

    def test_turtle_prompt_normalization(self):
        normalized = normalize_prompt_for_image_model("귀여운 거북이가 춤추는 GIF")
        hints = extract_scene_hints("귀여운 거북이가 춤추는 GIF")
        prompt = build_image_prompt(build_generation_request("귀여운 거북이가 춤추는 GIF", "cute3d", "9:16"))
        self.assertIn("cute turtle", normalized)
        self.assertIn("visible shell", normalized)
        self.assertIn("dancing motion", normalized)
        self.assertIn("a cute turtle as the main subject with a visible shell", hints)
        self.assertIn("do not replace it with a cat", prompt)

    def test_cherry_blossom_prompt_excludes_random_animals(self):
        normalized = normalize_prompt_for_image_model("벛꽃이 휘날리는 GIF")
        hints = extract_scene_hints("벛꽃이 휘날리는 GIF")
        prompt = build_image_prompt(build_generation_request("벛꽃이 휘날리는 GIF", "cute3d", "9:16"))
        self.assertIn("cherry blossom petals", normalized)
        self.assertTrue(any("pink cherry blossom trees and petals" in hint for hint in hints))
        self.assertIn("No cats, no dogs, no animals", prompt)


if __name__ == "__main__":
    unittest.main()
