# AI GIF Maker MVP

영어 프롬프트로 2D 스타일 3초 GIF를 생성하는 Flask + Pillow 기반 MVP입니다.

## 핵심 변경

- `POST /api/generate`로 GIF 생성
- 기본 스타일은 `2D 일러스트`
- `POLLINATIONS_ENABLED=1`이면 키 없이 Pollinations 무료 이미지 API를 먼저 사용
- OpenAI 이미지 API는 나중의 고급 유료화 옵션으로 보류
- Pollinations/OpenAI 호출이 실패하면 로컬 Pillow 생성기로 fallback
- 생성 파일은 `generated/`에 UUID 파일명으로 저장
- 모바일/카톡 브라우저 다운로드 우회를 위해 `/view/<filename>` 저장 페이지 제공
- 기본 저장 위치: `C:\Users\dwksh\Downloads\AI_GIF_Maker`
- IP 기준 인메모리 rate limit
- 간단한 부적절 요청 차단

## 실행

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python app.py
```

접속:

```text
http://127.0.0.1:5000
```

## Render 배포

이 프로젝트는 Render Web Service 배포용 파일을 포함합니다.

- `render.yaml`
- `Procfile`
- `runtime.txt`
- `requirements.txt`

Render 설정값:

```text
Build Command: pip install -r requirements.txt
Start Command: gunicorn --timeout 180 app:app
Health Check Path: /healthz
```

배포 순서:

1. 이 폴더를 GitHub 저장소로 업로드합니다.
2. Render Dashboard에서 `New > Web Service`를 선택합니다.
3. GitHub 저장소를 연결합니다.
4. Render가 `render.yaml`을 감지하면 그대로 생성합니다.
5. 배포가 끝나면 `https://...onrender.com` 주소가 생성됩니다.

주의:

- `.env`는 업로드하지 마세요. `.gitignore`에 제외되어 있습니다.
- 지금은 OpenAI를 끄고 Pollinations 무료 이미지 API를 기본 사용합니다.
- Render 무료/저가 인스턴스는 첫 접속이나 오랜 유휴 뒤에 느릴 수 있습니다.
- 생성된 GIF는 서버의 임시 디스크에 저장됩니다. 사용자는 화면의 `GIF 다운로드` 버튼으로 바로 내려받아야 합니다.

## OpenAI 이미지 API 설정

OpenAI는 현재 기본 비활성화 상태입니다. 나중에 고급 유료 플랜을 붙일 때만 `OPENAI_IMAGE_ENABLED=1`로 바꾸세요.

```text
OPENAI_API_KEY=sk-...
OPENAI_IMAGE_ENABLED=0
OPENAI_IMAGE_MODEL=gpt-image-2
OPENAI_IMAGE_QUALITY=low
```

비용을 낮추려면 유료화 전에는 `OPENAI_IMAGE_ENABLED=0`을 유지하세요. 활성화 후 API 호출이 실패해도 앱은 에러로 멈추지 않고 로컬 데모 생성기로 fallback합니다.

## Pollinations 무료 이미지 API 설정

기본값은 Pollinations를 먼저 사용합니다. 별도 API 키가 필요 없습니다.

```text
POLLINATIONS_ENABLED=1
POLLINATIONS_MODEL=flux
POLLINATIONS_TIMEOUT_SECONDS=90
```

생성 순서:

```text
Pollinations 무료 이미지 API -> 로컬 Pillow 데모 생성기
```

유료 고급 모드를 켜면 생성 순서는 다음처럼 확장됩니다.

```text
Pollinations 무료 이미지 API -> OpenAI 이미지 API -> 로컬 Pillow 데모 생성기
```

## 사용

1. 영어 GIF 설명을 입력합니다.
2. 스타일과 비율을 선택합니다.
3. `GIF 생성`을 누릅니다.
4. 미리보기가 뜨면 `GIF 다운로드` 또는 `모바일에서 GIF 열기/저장`을 누릅니다.
5. 휴대폰에서는 열린 GIF를 길게 눌러 저장할 수 있습니다.

예시:

```text
flat 2D cartoon cherry blossom petals blowing in the wind, clean composition, high quality
```

## Next.js + FastAPI 전환 계획

1. 현재 Flask 템플릿 UI를 Next.js 컴포넌트로 이전합니다.
2. FastAPI에 `generate`, `save-to-downloads`, `download` API를 구현합니다.
3. `LocalFrameGenerator`를 AI 이미지/프레임 API 어댑터로 교체합니다.
4. 긴 생성 작업은 큐 기반 비동기 작업으로 전환합니다.
5. 운영 저장소는 S3/R2로 교체하고 서명 URL을 반환합니다.

## 테스트

```bash
python -m unittest
```
