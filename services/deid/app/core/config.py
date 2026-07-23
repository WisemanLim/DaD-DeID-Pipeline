from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# 리포 루트 = services/deid/app/core/config.py 에서 parents[4]
_REPO_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env.local", extra="ignore")

    env: str = "local"
    database_url: str = "sqlite:///./local.db"
    redis_url: str = "redis://localhost:6379/0"
    # vault(재식별키/recipe token) + KMS/HSM 범위는 PRD 미결정 → 인터페이스만
    vault_url: str = "memory://"             # 구현 시 KMS/HSM 백엔드 주입
    policy_engine: str = "builtin"           # builtin | opa | cedar

    # 룰번들 로더 (Epic 0)
    seed_dir: str = str(_REPO_ROOT / ".docs" / "seed")
    default_locale: str = "kr"               # kr | en (seed 파일 접미사)

    # 검출기 토글 (Epic 1)
    enable_ner: bool = True                  # spaCy NER (인명/지명/기관)
    enable_dict: bool = True                 # 용어 사전 (영업비밀 등)


settings = Settings()
