from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

EMAIL_TEMPLATES_DIR = Path(__file__).resolve().parent


@lru_cache
def get_email_template_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(EMAIL_TEMPLATES_DIR),
        autoescape=select_autoescape(enabled_extensions=("html", "htm", "xml")),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_email_template(name: str, **context: object) -> str:
    """Render an email template from app/email_templates by filename."""
    return get_email_template_env().get_template(name).render(**context)
