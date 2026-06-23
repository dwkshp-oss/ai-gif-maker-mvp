from __future__ import annotations

import base64
from io import BytesIO
import math
import re

from PIL import Image

from gif_maker.config import AppConfig
from gif_maker.generator import GenerationRequest, STYLE_THEMES


OPENAI_SIZE_BY_RATIO = {
    "9:16": "1024x1536",
    "1:1": "1024x1024",
    "16:9": "1536x1024",
}

FRAME_SIZE_BY_RATIO = {
    "9:16": (576, 1024),
    "1:1": (768, 768),
    "16:9": (1024, 576),
}


class OpenAIImageGenerationError(RuntimeError):
    pass


class OpenAIImageFrameGenerator:
    def __init__(self, config: AppConfig):
        self.config = config

    @property
    def is_available(self) -> bool:
        return bool(self.config.openai_image_enabled and self.config.openai_api_key)

    def generate_frames(self, request: GenerationRequest) -> list[Image.Image]:
        image = self._generate_image(request)
        return make_animated_frames(image, request.ratio)

    def _generate_image(self, request: GenerationRequest) -> Image.Image:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise OpenAIImageGenerationError("openai package is not installed.") from exc

        client = OpenAI(api_key=self.config.openai_api_key)
        prompt = build_image_prompt(request)
        try:
            response = client.images.generate(
                model=self.config.openai_image_model,
                prompt=prompt,
                size=OPENAI_SIZE_BY_RATIO[request.ratio],
                quality=self.config.openai_image_quality,
                n=1,
            )
        except Exception as exc:
            raise OpenAIImageGenerationError(str(exc)) from exc

        try:
            b64_image = response.data[0].b64_json
            image_bytes = base64.b64decode(b64_image)
            return Image.open(BytesIO(image_bytes)).convert("RGB")
        except Exception as exc:
            raise OpenAIImageGenerationError("Could not decode image response.") from exc


def build_image_prompt(request: GenerationRequest) -> str:
    theme = STYLE_THEMES[request.style]["label"]
    style_instruction = image_style_instruction(request.style, theme)
    aspect = {
        "9:16": "vertical 9:16 short-form social media composition",
        "1:1": "square social media composition",
        "16:9": "wide 16:9 presentation composition",
    }[request.ratio]
    english_scene = normalize_prompt_for_image_model(request.prompt)
    scene_hints = extract_scene_hints(request.prompt)
    hint_sentence = ", ".join(scene_hints) if scene_hints else "follow the user's exact subject and action"
    exclusion_sentence = build_exclusion_sentence(english_scene, request.prompt)

    return (
        "Create ONE image that faithfully depicts this exact visual scene. "
        f"Primary English scene description: {english_scene}. "
        f"Original user request for reference only: {request.prompt}. "
        f"Required visible elements: {hint_sentence}. "
        f"{exclusion_sentence} "
        f"Visual style: {style_instruction}. Composition: {aspect}. "
        "The generated image must match the primary English scene description. "
        "If a specific animal is requested, draw that exact animal species and do not replace it with a cat, dog, or person. "
        "Prioritize the exact subject, object, action, and setting over generic style. "
        "Do not invent unrelated characters or objects. "
        "No text, no captions, no watermark, no UI, no logo, no extra symbols."
    )


def image_style_instruction(style: str, theme_label: str) -> str:
    if style == "flat2d":
        return (
            "clean flat 2D illustration, simple vector cartoon style, bold readable shapes, "
            "smooth cel animation look, bright colors, no 3D render, no photorealism, no realistic photo texture"
        )
    if style == "cute3d":
        return "cute soft 3D rendered style, rounded shapes, playful lighting"
    if style == "meme":
        return "simple meme-style illustration, expressive, bold composition"
    if style == "business":
        return "clean business presentation illustration, polished and simple"
    if style == "pet":
        return "cute pet illustration, friendly and warm"
    return theme_label


def normalize_prompt_for_image_model(prompt: str) -> str:
    cleaned = " ".join(prompt.strip().split())
    if not contains_hangul(cleaned):
        return cleaned

    lowered = cleaned.lower()
    phrases = []
    phrase_rules = [
        (("커피잔", "커피 컵", "커피", "카페"), "a clearly visible coffee cup"),
        (("아이디어", "영감"), "a glowing idea light bulb above the main subject"),
        (("반짝", "빛나는", "빛", "스파클"), "sparkling light particles"),
        (("벚꽃", "벛꽃", "벚꽃잎", "벛꽃잎", "cherry blossom", "sakura"), "pink cherry blossom petals blowing in the wind"),
        (("꽃잎", "꽃잎이", "petal", "petals"), "flower petals floating through the air"),
        (("강아지", "개", " puppy", "dog"), "a cute dog"),
        (("고양이", " cat", "kitten"), "a cute cat"),
        (("거북이", "거북", "turtle", "tortoise"), "a cute turtle with a visible shell"),
        (("토끼", "rabbit", "bunny"), "a cute rabbit with long ears"),
        (("새", "bird"), "a cute bird"),
        (("햄스터", "hamster"), "a cute hamster"),
        (("펭귄", "penguin"), "a cute penguin"),
        (("반려동물",), "a cute pet"),
        (("제품", "상품"), "a product showcase"),
        (("발표", "프레젠테이션", "피치"), "a presentation scene"),
        (("회사", "회의", "사무실", "비즈니스"), "a modern business office setting"),
        (("바다", "해변"), "a beach and ocean background"),
        (("산", "등산"), "a mountain landscape"),
        (("비행기", "여행"), "a travel scene with an airplane motif"),
        (("피자",), "a pizza"),
        (("케이크",), "a cake"),
        (("햄버거", "버거"), "a burger"),
        (("귀여운", "귀엽"), "cute and friendly"),
        (("3d", "3D"), "soft 3D rendered style"),
        (("밈",), "funny meme-like reaction style"),
    ]
    for keywords, phrase in phrase_rules:
        if any(keyword.lower() in lowered for keyword in keywords):
            phrases.append(phrase)

    if not phrases:
        return f"a clear image matching this Korean request: {cleaned}"

    action = infer_action(lowered)
    return ", ".join(unique_preserve_order(phrases + [action, "clean composition", "high quality"]))


def infer_action(lowered_prompt: str) -> str:
    if "떠오" in lowered_prompt or "올라" in lowered_prompt:
        return "the key object is floating upward"
    if "달리" in lowered_prompt or "뛰" in lowered_prompt:
        return "dynamic running motion"
    if "춤" in lowered_prompt:
        return "dancing motion"
    if "먹" in lowered_prompt:
        return "eating action"
    if "마시" in lowered_prompt:
        return "drinking action"
    if "보" in lowered_prompt:
        return "the subject is looking at the main object"
    return "the scene is easy to understand at a glance"


def extract_scene_hints(prompt: str) -> list[str]:
    lowered = prompt.lower()
    rules = [
        (("커피", "coffee", "카페", "latte"), "a clearly visible coffee cup"),
        (("아이디어", "idea", "영감"), "a glowing idea light above the main subject"),
        (("반짝", "spark", "shine", "빛"), "sparkling light particles"),
        (("강아지", "dog", "puppy", "개"), "a cute dog as the main subject"),
        (("고양이", "cat", "kitten"), "a cute cat as the main subject"),
        (("거북이", "거북", "turtle", "tortoise"), "a cute turtle as the main subject with a visible shell"),
        (("토끼", "rabbit", "bunny"), "a cute rabbit as the main subject with long ears"),
        (("새", "bird"), "a cute bird as the main subject"),
        (("햄스터", "hamster"), "a cute hamster as the main subject"),
        (("펭귄", "penguin"), "a cute penguin as the main subject"),
        (("제품", "product", "상품"), "a product showcase scene"),
        (("발표", "presentation", "pitch", "프레젠테이션"), "a presentation or pitch scene"),
        (("회의", "office", "business", "사무실", "회사"), "a modern business office setting"),
        (("바다", "beach", "ocean", "해변"), "a beach or ocean background"),
        (("산", "mountain"), "a mountain landscape background"),
        (("벚꽃", "벛꽃", "cherry blossom", "sakura"), "pink cherry blossom trees and petals blowing in the wind"),
        (("꽃잎", "petal", "petals"), "visible flower petals floating through the air"),
        (("비행기", "flight", "airplane", "여행"), "an airplane or travel motif"),
        (("피자", "pizza"), "a pizza as the main food object"),
        (("케이크", "cake"), "a cake as the main food object"),
        (("햄버거", "burger"), "a burger as the main food object"),
    ]
    hints = []
    for keywords, hint in rules:
        if any(keyword in lowered for keyword in keywords):
            hints.append(hint)
    return hints[:7]


def build_exclusion_sentence(*texts: str) -> str:
    joined = " ".join(texts).lower()
    if has_requested_animal(joined) or has_requested_person(joined):
        return "Do not add unrelated animals, people, or extra characters."
    return "No cats, no dogs, no animals, no people, no characters; only the requested scene elements."


def has_requested_animal(text: str) -> bool:
    korean_animal_keywords = (
        "고양이",
        "강아지",
        "거북이",
        "거북",
        "토끼",
        "새",
        "햄스터",
        "펭귄",
        "반려동물",
    )
    english_animal_keywords = (
        "cat",
        "kitten",
        "dog",
        "puppy",
        "turtle",
        "tortoise",
        "rabbit",
        "bunny",
        "bird",
        "hamster",
        "penguin",
        "pet",
    )
    return any(keyword in text for keyword in korean_animal_keywords) or any(
        re.search(rf"\b{re.escape(keyword)}\b", text) for keyword in english_animal_keywords
    )


def has_requested_person(text: str) -> bool:
    person_keywords = ("사람", "인물", "남자", "여자", "아이", "person", "people", "man", "woman", "child")
    return any(keyword in text for keyword in person_keywords)


def contains_hangul(text: str) -> bool:
    return bool(re.search(r"[가-힣]", text))


def unique_preserve_order(items: list[str]) -> list[str]:
    seen = set()
    unique = []
    for item in items:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def make_animated_frames(image: Image.Image, ratio: str, frame_count: int = 25) -> list[Image.Image]:
    width, height = FRAME_SIZE_BY_RATIO[ratio]
    image = crop_to_ratio(image, width / height)
    frames = []
    for index in range(frame_count):
        t = index / max(1, frame_count - 1)
        zoom = 1.0 + 0.045 * math.sin(t * math.pi)
        pan_x = int(math.sin(t * math.pi * 2) * width * 0.018)
        pan_y = int(math.cos(t * math.pi * 2) * height * 0.012)
        resized = image.resize((int(width * zoom), int(height * zoom)), Image.Resampling.LANCZOS)
        left = (resized.width - width) // 2 + pan_x
        top = (resized.height - height) // 2 + pan_y
        left = max(0, min(left, resized.width - width))
        top = max(0, min(top, resized.height - height))
        frame = resized.crop((left, top, left + width, top + height))
        frames.append(frame.convert("P", palette=Image.Palette.ADAPTIVE))
    return frames


def crop_to_ratio(image: Image.Image, target_ratio: float) -> Image.Image:
    source_ratio = image.width / image.height
    if source_ratio > target_ratio:
        new_width = int(image.height * target_ratio)
        left = (image.width - new_width) // 2
        return image.crop((left, 0, left + new_width, image.height))
    new_height = int(image.width / target_ratio)
    top = (image.height - new_height) // 2
    return image.crop((0, top, image.width, top + new_height))
