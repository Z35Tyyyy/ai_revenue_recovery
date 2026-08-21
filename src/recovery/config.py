"""Central configuration.

All secrets are optional. The engine is designed to run end-to-end with zero
credentials (deterministic LLM fallback + mocked Razorpay gateway), so that a
reviewer can clone the repo and run ``make all`` with nothing configured.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=".env",
        extra="ignore",
        protected_namespaces=(),
    )

    # Reproducibility
    seed: int = Field(default=7, alias="RECOVERY_SEED")

    # Filesystem
    data_dir: Path = Field(default=REPO_ROOT / "data", alias="RECOVERY_DATA_DIR")
    model_dir: Path = Field(default=REPO_ROOT / "models", alias="RECOVERY_MODEL_DIR")
    report_dir: Path = Field(default=REPO_ROOT / "reports")

    # Razorpay (test mode)
    razorpay_key_id: str | None = Field(default=None, alias="RAZORPAY_KEY_ID")
    razorpay_key_secret: str | None = Field(default=None, alias="RAZORPAY_KEY_SECRET")
    razorpay_webhook_secret: str | None = Field(default=None, alias="RAZORPAY_WEBHOOK_SECRET")

    # Anthropic / Claude
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    llm_model: str = Field(default="claude-sonnet-5", alias="RECOVERY_LLM_MODEL")

    @property
    def razorpay_enabled(self) -> bool:
        return bool(self.razorpay_key_id and self.razorpay_key_secret)

    @property
    def llm_enabled(self) -> bool:
        return bool(self.anthropic_api_key)

    def ensure_dirs(self) -> None:
        for d in (self.data_dir, self.model_dir, self.report_dir):
            Path(d).mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
