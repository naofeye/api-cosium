"""Tests du moteur de detection et scoring des renouvellements."""


from app.domain.schemas.renewals import RenewalConfig
from app.services.renewal_engine import _build_reason, _score_opportunity, _suggest_action


def test_score_minimum_age():
    """Un client a l'anciennete minimum a un score modere."""
    config = RenewalConfig(age_minimum_months=24)
    score = _score_opportunity(
        months_since=24, last_amount=500, has_mutuelle=False, config=config,
    )
    assert 15 <= score <= 60
    assert isinstance(score, float)


def test_score_increases_with_age():
    """Plus l'achat est ancien, plus le score augmente."""
    config = RenewalConfig(age_minimum_months=24)
    score_24 = _score_opportunity(24, 500, False, config)
    score_36 = _score_opportunity(36, 500, False, config)
    score_48 = _score_opportunity(48, 500, False, config)
    assert score_24 < score_36 < score_48


def test_score_increases_with_amount():
    """Les clients a forte valeur ont un meilleur score."""
    config = RenewalConfig(age_minimum_months=24)
    score_low = _score_opportunity(30, 100, False, config)
    score_high = _score_opportunity(30, 800, False, config)
    assert score_low < score_high


def test_score_mutuelle_bonus():
    """La mutuelle active ajoute un bonus au score."""
    config = RenewalConfig(age_minimum_months=24, mutuelle_bonus=15)
    score_no = _score_opportunity(30, 500, False, config)
    score_yes = _score_opportunity(30, 500, True, config)
    assert score_yes - score_no == 15.0


def test_score_capped_at_100():
    """Le score ne depasse jamais 100."""
    config = RenewalConfig(age_minimum_months=24, mutuelle_bonus=50)
    score = _score_opportunity(60, 2000, True, config)
    assert score <= 100.0


def test_suggest_action_high_score_phone():
    """Les clients a fort score avec telephone = appel."""
    action = _suggest_action(75, has_email=True, has_phone=True)
    assert action == "telephone"


def test_suggest_action_email_default():
    """Le canal par defaut est l'email si disponible."""
    action = _suggest_action(50, has_email=True, has_phone=True)
    assert action == "email"


def test_suggest_action_sms_fallback():
    """SMS si pas d'email mais telephone disponible."""
    action = _suggest_action(50, has_email=False, has_phone=True)
    assert action == "sms"


def test_suggest_action_courrier_last_resort():
    """Courrier si aucun canal electronique."""
    action = _suggest_action(50, has_email=False, has_phone=False)
    assert action == "courrier"


def test_build_reason_basic():
    reason = _build_reason(30, None, False)
    assert "30 mois" in reason


def test_build_reason_with_equipment():
    reason = _build_reason(24, "monture", False)
    assert "monture" in reason.lower()


def test_build_reason_with_mutuelle():
    reason = _build_reason(24, None, True)
    assert "mutuelle" in reason.lower()


def test_renewal_config_defaults():
    """La config par defaut est valide."""
    config = RenewalConfig()
    assert config.age_minimum_months == 24
    assert config.mutuelle_bonus == 15.0
    assert len(config.equipment_types) > 0


def test_renewal_config_custom():
    """La config accepte des valeurs personnalisees."""
    config = RenewalConfig(age_minimum_months=12, mutuelle_bonus=20)
    assert config.age_minimum_months == 12
    assert config.mutuelle_bonus == 20
