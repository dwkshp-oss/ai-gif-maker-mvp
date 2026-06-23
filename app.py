from flask import Flask, jsonify, render_template, request, send_file, send_from_directory

from gif_maker.config import AppConfig
from gif_maker.generator import LocalFrameGenerator, build_generation_request
from gif_maker.moderation import ModerationError, validate_prompt
from gif_maker.openai_image import (
    OpenAIImageFrameGenerator,
    OpenAIImageGenerationError,
    normalize_prompt_for_image_model,
)
from gif_maker.pollinations_image import PollinationsFrameGenerator, PollinationsImageGenerationError
from gif_maker.rate_limit import InMemoryRateLimiter
from gif_maker.storage import LocalGifStorage


def create_app(config: AppConfig | None = None) -> Flask:
    config = config or AppConfig.from_env()
    app = Flask(__name__)
    app.config["APP_CONFIG"] = config

    storage = LocalGifStorage(config.generated_dir, config.download_dir)
    local_generator = LocalFrameGenerator()
    pollinations_generator = PollinationsFrameGenerator(config)
    openai_generator = OpenAIImageFrameGenerator(config)
    limiter = InMemoryRateLimiter(config.rate_limit_count, config.rate_limit_window_seconds)

    @app.get("/")
    def index():
        return render_template(
            "index.html",
            styles=local_generator.available_styles(),
            ratios=local_generator.available_ratios(),
            default_ratio=config.default_ratio,
            download_to_server_enabled=config.download_to_server_enabled,
        )

    @app.get("/healthz")
    def healthz():
        return jsonify({"ok": True})

    @app.post("/api/translate-prompt")
    def translate_prompt():
        data = request.get_json(silent=True) or {}
        prompt = str(data.get("prompt", "")).strip()
        if not prompt:
            return jsonify({"ok": False, "message": "프롬프트를 입력해 주세요."}), 400

        english_prompt = normalize_prompt_for_image_model(prompt)
        return jsonify(
            {
                "ok": True,
                "englishPrompt": english_prompt,
                "note": "무료 이미지 모델이 더 잘 이해하도록 영어 이미지 지시문으로 바꿨습니다.",
            }
        )

    @app.post("/api/generate")
    def generate():
        client_ip = request.headers.get("X-Forwarded-For", request.remote_addr or "local")
        client_ip = client_ip.split(",")[0].strip()

        if not limiter.allow(client_ip):
            return jsonify(
                {
                    "ok": False,
                    "error": "RATE_LIMITED",
                    "message": "요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.",
                }
            ), 429

        data = request.get_json(silent=True) or {}
        source_prompt = str(data.get("prompt", "")).strip()
        image_prompt = str(data.get("englishPrompt", "")).strip() or source_prompt

        try:
            generation_request = build_generation_request(
                prompt=image_prompt,
                style=data.get("style", config.default_style),
                ratio=data.get("ratio", config.default_ratio),
            )
            validate_prompt(generation_request.prompt)
        except ModerationError as exc:
            return jsonify({"ok": False, "error": "REJECTED_PROMPT", "message": str(exc)}), 400
        except ValueError as exc:
            return jsonify({"ok": False, "error": "BAD_REQUEST", "message": str(exc)}), 400

        frames, provider, provider_note = generate_frames_with_fallback(
            generation_request,
            pollinations_generator,
            openai_generator,
            local_generator,
            config,
        )
        filename = storage.save_gif(frames, duration_ms=config.frame_duration_ms)

        return jsonify(
            {
                "ok": True,
                "url": storage.public_url(filename),
                "downloadUrl": f"/download/{filename}",
                "saveUrl": "/api/save-to-downloads",
                "filename": filename,
                "downloadToServerEnabled": config.download_to_server_enabled,
                "metadata": {
                    "sourcePrompt": source_prompt,
                    "imagePrompt": generation_request.prompt,
                    "durationSeconds": config.gif_duration_seconds,
                    "frameCount": len(frames),
                    "ratio": generation_request.ratio,
                    "style": generation_request.style,
                    "provider": provider,
                    "note": provider_note,
                },
            }
        )

    @app.post("/api/save-to-downloads")
    def save_to_downloads():
        if not config.download_to_server_enabled:
            return jsonify(
                {
                    "ok": False,
                    "message": "클라우드 배포 환경에서는 브라우저 직접 다운로드를 사용해 주세요.",
                }
            ), 403

        data = request.get_json(silent=True) or {}
        filename = data.get("filename", "")
        try:
            saved_path = storage.copy_to_downloads(filename)
        except (FileNotFoundError, ValueError) as exc:
            return jsonify({"ok": False, "message": str(exc)}), 404

        return jsonify(
            {
                "ok": True,
                "path": str(saved_path),
                "message": f"GIF 파일을 저장했습니다: {saved_path}",
            }
        )

    @app.get("/generated/<filename>")
    def generated_file(filename):
        return send_from_directory(storage.output_dir, filename)

    @app.get("/download/<filename>")
    def download(filename):
        path = storage.path_for(filename)
        response = send_file(
            path,
            mimetype="image/gif",
            as_attachment=True,
            download_name=filename,
            max_age=0,
        )
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    return app


def generate_frames_with_fallback(
    generation_request,
    pollinations_generator,
    openai_generator,
    local_generator,
    config: AppConfig,
):
    provider_errors = []

    if pollinations_generator.is_available:
        try:
            frames = pollinations_generator.generate_frames(generation_request)
            return (
                frames,
                f"pollinations-{config.pollinations_model}",
                "Pollinations 무료 이미지 API로 원본 이미지를 만들고 3초 GIF로 변환했습니다.",
            )
        except PollinationsImageGenerationError as exc:
            provider_errors.append(f"Pollinations 실패: {exc}")

    if openai_generator.is_available:
        try:
            frames = openai_generator.generate_frames(generation_request)
            return (
                frames,
                config.openai_image_model,
                "OpenAI 이미지 API로 원본 이미지를 만들고 3초 GIF로 변환했습니다.",
            )
        except OpenAIImageGenerationError as exc:
            provider_errors.append(f"OpenAI 실패: {exc}")

    frames = local_generator.generate_frames(generation_request)
    if provider_errors:
        note = "무료/AI 이미지 생성 실패로 로컬 데모 생성기를 사용했습니다. " + " | ".join(provider_errors)
    else:
        note = "무료/AI 이미지 생성기가 꺼져 있어 로컬 데모 생성기를 사용했습니다."
    return frames, "local-pillow-demo", note


app = create_app()


if __name__ == "__main__":
    app.run(
        debug=app.config["APP_CONFIG"].debug,
        host=app.config["APP_CONFIG"].host,
        port=app.config["APP_CONFIG"].port,
    )
