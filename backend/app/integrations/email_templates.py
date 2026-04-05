from pathlib import Path

from jinja2 import Environment, FileSystemLoader

_TEMPLATE_DIR = Path(__file__).parent.parent / "templates"
_env = Environment(loader=FileSystemLoader(str(_TEMPLATE_DIR)), autoescape=True)


def render_email(template_name: str, **context: object) -> str:
    """Render an email template with the given context variables."""
    template = _env.get_template(template_name)
    return template.render(**context)
