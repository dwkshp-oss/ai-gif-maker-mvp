import re


class ModerationError(ValueError):
    pass


BLOCKED_PATTERNS = [
    r"\b(?:nude|porn|sexual|explicit)\b",
    r"\b(?:kill|murder|suicide|self[- ]?harm)\b",
    r"(?:나체|포르노|성적|자살|살해|혐오)",
]


def validate_prompt(prompt: str) -> None:
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, prompt, re.IGNORECASE):
            raise ModerationError("해당 요청은 안전 정책상 생성할 수 없습니다.")
