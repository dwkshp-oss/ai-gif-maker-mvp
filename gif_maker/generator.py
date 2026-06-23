from dataclasses import dataclass
import math
import os
import textwrap

from PIL import Image, ImageDraw, ImageFilter, ImageFont


STYLE_THEMES = {
    "cute3d": {
        "label": "귀여운 3D",
        "bg": [(255, 242, 210), (255, 210, 228)],
        "accent": (80, 52, 120),
    },
    "meme": {
        "label": "밈",
        "bg": [(250, 250, 250), (220, 235, 255)],
        "accent": (15, 15, 15),
    },
    "business": {
        "label": "비즈니스",
        "bg": [(230, 240, 255), (235, 255, 245)],
        "accent": (30, 58, 138),
    },
    "pet": {
        "label": "반려동물",
        "bg": [(235, 255, 235), (255, 238, 210)],
        "accent": (80, 80, 45),
    },
}

RATIO_SIZES = {
    "9:16": (576, 1024),
    "1:1": (768, 768),
    "16:9": (1024, 576),
}

SCENE_KEYWORDS = {
    "coffee": ("커피", "coffee", "cafe", "latte", "카페"),
    "pet": ("강아지", "고양이", "반려", "pet", "dog", "cat", "puppy", "kitten"),
    "business": ("제품", "발표", "비즈니스", "회사", "회의", "매출", "product", "business", "office", "presentation"),
    "idea": ("아이디어", "반짝", "빛", "spark", "idea", "light", "shine"),
    "travel": ("여행", "바다", "산", "비행기", "travel", "beach", "mountain", "flight"),
    "food": ("음식", "케이크", "피자", "버거", "food", "cake", "pizza", "burger"),
}


@dataclass(frozen=True)
class GenerationRequest:
    prompt: str
    style: str
    ratio: str


@dataclass(frozen=True)
class ScenePlan:
    scene: str
    title: str
    color: tuple[int, int, int]
    has_spark: bool = False


def build_generation_request(prompt: str, style: str, ratio: str) -> GenerationRequest:
    cleaned_prompt = " ".join(str(prompt or "").strip().split())
    if not cleaned_prompt:
        raise ValueError("GIF 설명을 입력해 주세요.")
    if len(cleaned_prompt) > 300:
        cleaned_prompt = cleaned_prompt[:300]
    if style not in STYLE_THEMES:
        raise ValueError("지원하지 않는 스타일입니다.")
    if ratio not in RATIO_SIZES:
        raise ValueError("지원하지 않는 비율입니다.")
    return GenerationRequest(cleaned_prompt, style, ratio)


class LocalFrameGenerator:
    def available_styles(self) -> dict:
        return STYLE_THEMES

    def available_ratios(self) -> dict:
        return {
            "9:16": "9:16 쇼츠",
            "1:1": "1:1 SNS",
            "16:9": "16:9 와이드",
        }

    def generate_frames(self, request: GenerationRequest) -> list[Image.Image]:
        width, height = RATIO_SIZES[request.ratio]
        theme = STYLE_THEMES[request.style]
        scene_plan = plan_scene(request.prompt, request.style)
        frames = []
        frame_count = 25
        font_big = get_font(50 if request.ratio == "9:16" else 42)
        font_small = get_font(26)
        label_font = get_font(34)
        prompt_text = wrap_prompt(request.prompt)

        for index in range(frame_count):
            t = index / frame_count
            img = gradient_background(width, height, theme["bg"][0], theme["bg"][1]).convert("RGBA")
            draw = ImageDraw.Draw(img)
            add_motion_blob(img, width, height, scene_plan.color, t)
            draw_scene(draw, width, height, scene_plan, t)
            if scene_plan.has_spark:
                draw_sparkles(draw, width, height, scene_plan.color, t)
            add_scene_label(draw, width, height, scene_plan.title, label_font, theme["accent"])
            add_prompt(draw, width, height, prompt_text, font_big, theme["accent"])
            add_footer(draw, width, height, font_small)
            frames.append(img.convert("P", palette=Image.Palette.ADAPTIVE))

        return frames


def plan_scene(prompt: str, style: str) -> ScenePlan:
    lowered = prompt.lower()
    for scene, keywords in SCENE_KEYWORDS.items():
        if any(keyword.lower() in lowered for keyword in keywords):
            base = scene_plan_for(scene)
            return ScenePlan(base.scene, base.title, base.color, has_spark=has_spark_prompt(lowered))
    if style == "pet":
        return scene_plan_for("pet")
    if style == "business":
        return scene_plan_for("business")
    if style == "meme":
        return ScenePlan("meme", "Meme reaction", (20, 20, 20))
    return ScenePlan("idea", "Spark idea", (255, 190, 60), has_spark=True)


def has_spark_prompt(lowered_prompt: str) -> bool:
    return any(keyword in lowered_prompt for keyword in ("아이디어", "반짝", "빛", "spark", "idea", "light", "shine"))


def scene_plan_for(scene: str) -> ScenePlan:
    plans = {
        "coffee": ScenePlan("coffee", "Coffee moment", (137, 83, 42)),
        "pet": ScenePlan("pet", "Pet scene", (92, 130, 72)),
        "business": ScenePlan("business", "Product pitch", (36, 86, 214)),
        "idea": ScenePlan("idea", "Spark idea", (255, 190, 60)),
        "travel": ScenePlan("travel", "Travel vibe", (42, 157, 143)),
        "food": ScenePlan("food", "Tasty scene", (230, 126, 34)),
    }
    return plans[scene]


def get_font(size: int = 64) -> ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/malgun.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def gradient_background(width: int, height: int, c1: tuple, c2: tuple) -> Image.Image:
    img = Image.new("RGB", (width, height), c1)
    px = img.load()
    for y in range(height):
        ratio = y / max(1, height - 1)
        r = int(c1[0] * (1 - ratio) + c2[0] * ratio)
        g = int(c1[1] * (1 - ratio) + c2[1] * ratio)
        b = int(c1[2] * (1 - ratio) + c2[2] * ratio)
        for x in range(width):
            px[x, y] = (r, g, b)
    return img


def wrap_prompt(prompt: str, max_chars: int = 16) -> str:
    return "\n".join(textwrap.wrap(prompt, width=max_chars)[:3])


def add_motion_blob(img: Image.Image, width: int, height: int, accent: tuple, t: float) -> None:
    cx = width // 2 + int(math.sin(t * math.pi * 2) * 36)
    cy = int(height * 0.34) + int(math.cos(t * math.pi * 2) * 22)
    radius = int(min(width, height) * (0.25 + 0.025 * math.sin(t * math.pi * 2)))
    blob = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    bd = ImageDraw.Draw(blob)
    bd.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=(*accent, 34))
    bd.ellipse((cx - radius + 18, cy - radius + 18, cx + radius - 18, cy + radius - 18), fill=(255, 255, 255, 160))
    img.alpha_composite(blob.filter(ImageFilter.GaussianBlur(7)))


def draw_scene(draw: ImageDraw.ImageDraw, width: int, height: int, plan: ScenePlan, t: float) -> None:
    cx = width // 2
    cy = int(height * 0.34)
    bob = int(math.sin(t * math.pi * 2) * 14)
    scene = plan.scene
    if scene == "coffee":
        draw_coffee(draw, cx, cy + bob, plan.color)
    elif scene == "pet":
        draw_pet(draw, cx, cy + bob, plan.color)
    elif scene == "business":
        draw_business(draw, cx, cy + bob, plan.color)
    elif scene == "travel":
        draw_travel(draw, cx, cy + bob, plan.color)
    elif scene == "food":
        draw_food(draw, cx, cy + bob, plan.color)
    elif scene == "meme":
        draw_meme(draw, cx, cy + bob)
    else:
        draw_idea(draw, cx, cy + bob, plan.color, t)


def draw_coffee(draw: ImageDraw.ImageDraw, cx: int, cy: int, color: tuple) -> None:
    draw.rounded_rectangle((cx - 92, cy - 10, cx + 82, cy + 98), radius=24, fill=(255, 255, 255), outline=color, width=7)
    draw.arc((cx + 58, cy + 10, cx + 138, cy + 82), 270, 90, fill=color, width=10)
    draw.ellipse((cx - 78, cy - 32, cx + 68, cy + 18), fill=(116, 73, 42), outline=color, width=5)
    for x in (-45, 0, 42):
        draw.arc((cx + x - 18, cy - 104, cx + x + 18, cy - 32), 90, 250, fill=color, width=5)


def draw_pet(draw: ImageDraw.ImageDraw, cx: int, cy: int, color: tuple) -> None:
    draw.ellipse((cx - 88, cy - 76, cx + 88, cy + 100), fill=(255, 246, 226), outline=color, width=7)
    draw.polygon([(cx - 70, cy - 48), (cx - 116, cy - 116), (cx - 22, cy - 72)], fill=(255, 226, 180), outline=color)
    draw.polygon([(cx + 70, cy - 48), (cx + 116, cy - 116), (cx + 22, cy - 72)], fill=(255, 226, 180), outline=color)
    draw.ellipse((cx - 42, cy - 18, cx - 18, cy + 8), fill=color)
    draw.ellipse((cx + 18, cy - 18, cx + 42, cy + 8), fill=color)
    draw.ellipse((cx - 18, cy + 20, cx + 18, cy + 48), fill=(60, 45, 38))
    draw.arc((cx - 46, cy + 28, cx, cy + 78), 0, 70, fill=color, width=5)
    draw.arc((cx, cy + 28, cx + 46, cy + 78), 110, 180, fill=color, width=5)


def draw_business(draw: ImageDraw.ImageDraw, cx: int, cy: int, color: tuple) -> None:
    draw.rounded_rectangle((cx - 122, cy - 86, cx + 122, cy + 90), radius=16, fill=(255, 255, 255), outline=color, width=7)
    draw.rectangle((cx - 92, cy - 42, cx + 92, cy - 26), fill=(220, 230, 255))
    bars = [58, 86, 118]
    for i, h in enumerate(bars):
        x = cx - 68 + i * 54
        draw.rounded_rectangle((x, cy + 48 - h, x + 30, cy + 48), radius=6, fill=color)
    draw.line((cx - 78, cy + 58, cx + 84, cy + 58), fill=(90, 100, 120), width=5)


def draw_idea(draw: ImageDraw.ImageDraw, cx: int, cy: int, color: tuple, t: float) -> None:
    pulse = int(8 * math.sin(t * math.pi * 2))
    draw.ellipse((cx - 70 - pulse, cy - 100 - pulse, cx + 70 + pulse, cy + 40 + pulse), fill=(255, 246, 160), outline=color, width=7)
    draw.rounded_rectangle((cx - 34, cy + 34, cx + 34, cy + 92), radius=10, fill=(255, 255, 255), outline=color, width=6)
    for angle in range(0, 360, 45):
        rad = math.radians(angle)
        x1 = cx + int(math.cos(rad) * 102)
        y1 = cy - 30 + int(math.sin(rad) * 102)
        x2 = cx + int(math.cos(rad) * 136)
        y2 = cy - 30 + int(math.sin(rad) * 136)
        draw.line((x1, y1, x2, y2), fill=color, width=5)


def draw_travel(draw: ImageDraw.ImageDraw, cx: int, cy: int, color: tuple) -> None:
    draw.polygon([(cx - 150, cy + 70), (cx - 50, cy - 86), (cx + 10, cy + 70)], fill=(130, 190, 150), outline=color)
    draw.polygon([(cx - 20, cy + 70), (cx + 86, cy - 110), (cx + 156, cy + 70)], fill=(96, 170, 190), outline=color)
    draw.line((cx - 130, cy - 28, cx + 138, cy - 76), fill=color, width=8)
    draw.polygon([(cx + 126, cy - 78), (cx + 82, cy - 104), (cx + 94, cy - 68)], fill=color)


def draw_food(draw: ImageDraw.ImageDraw, cx: int, cy: int, color: tuple) -> None:
    draw.ellipse((cx - 118, cy - 38, cx + 118, cy + 82), fill=(255, 230, 190), outline=color, width=7)
    draw.ellipse((cx - 88, cy - 76, cx + 88, cy + 38), fill=(255, 246, 230), outline=color, width=5)
    for x, y in [(-42, -28), (22, -18), (52, 12), (-12, 18)]:
        draw.ellipse((cx + x - 10, cy + y - 10, cx + x + 10, cy + y + 10), fill=(220, 70, 70))


def draw_meme(draw: ImageDraw.ImageDraw, cx: int, cy: int) -> None:
    draw.ellipse((cx - 90, cy - 90, cx + 90, cy + 90), fill=(255, 235, 90), outline=(20, 20, 20), width=7)
    draw.ellipse((cx - 54, cy - 30, cx - 20, cy + 4), fill=(20, 20, 20))
    draw.ellipse((cx + 20, cy - 30, cx + 54, cy + 4), fill=(20, 20, 20))
    draw.arc((cx - 50, cy + 10, cx + 50, cy + 72), 10, 170, fill=(20, 20, 20), width=8)
    draw.text((cx - 78, cy - 150), "WOW", font=get_font(44), fill=(20, 20, 20))


def draw_sparkles(draw: ImageDraw.ImageDraw, width: int, height: int, color: tuple, t: float) -> None:
    center_y = int(height * 0.24)
    offset = int(math.sin(t * math.pi * 2) * 10)
    points = [
        (int(width * 0.30), center_y + offset),
        (int(width * 0.68), center_y - offset),
        (int(width * 0.52), center_y - 82 + offset),
    ]
    for x, y in points:
        draw.line((x - 18, y, x + 18, y), fill=color, width=5)
        draw.line((x, y - 18, x, y + 18), fill=color, width=5)
        draw.line((x - 12, y - 12, x + 12, y + 12), fill=(255, 255, 255), width=3)


def add_scene_label(draw: ImageDraw.ImageDraw, width: int, height: int, label: str, font: ImageFont.ImageFont, accent: tuple) -> None:
    bbox = draw.textbbox((0, 0), label, font=font)
    text_width = bbox[2] - bbox[0]
    x = (width - text_width) // 2
    y = int(height * 0.49)
    draw.rounded_rectangle((x - 18, y - 9, x + text_width + 18, y + 42), radius=14, fill=(255, 255, 255, 170))
    draw.text((x, y), label, font=font, fill=accent)


def add_prompt(draw: ImageDraw.ImageDraw, width: int, height: int, text: str, font: ImageFont.ImageFont, accent: tuple) -> None:
    bbox = draw.multiline_textbbox((0, 0), text, font=font, spacing=12, align="center")
    x = (width - (bbox[2] - bbox[0])) // 2
    y = int(height * 0.60)
    draw.multiline_text((x + 3, y + 3), text, font=font, fill=(255, 255, 255, 190), spacing=12, align="center")
    draw.multiline_text((x, y), text, font=font, fill=accent, spacing=12, align="center")


def add_footer(draw: ImageDraw.ImageDraw, width: int, height: int, font: ImageFont.ImageFont) -> None:
    footer = "AI GIF Maker MVP - local scene draft"
    bbox = draw.textbbox((0, 0), footer, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (width - text_width) // 2
    y = height - 92
    draw.rounded_rectangle((x - 24, y - 14, x + text_width + 24, y + text_height + 14), radius=28, fill=(255, 255, 255, 140))
    draw.text((x, y), footer, font=font, fill=(40, 40, 40, 220))
