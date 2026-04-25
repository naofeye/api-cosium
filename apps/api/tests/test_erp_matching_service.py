"""Tests unitaires pour app/services/erp_matching_service.py.

Couvre :
- Normalisation des noms (_normalize_name)
- Normalisation des numeros de telephone (_normalize_phone)
- Matching client par nom (_match_customer_by_name) :
    - Correspondance exacte
    - Strip du prefixe de civilite (M., Mme., etc.)
    - Inversion prenom/nom
    - Matching partiel (2 premiers mots, 2 derniers mots)
    - Fuzzy matching (rapidfuzz)
    - Aucune correspondance -> None
- Validation des donnees ERP (_validate_erp_customer_data)
- Detection de changements (_customer_has_changes)
- Mise a jour des champs (_update_customer_fields)
- Creation d'un client depuis l'ERP (_create_customer_from_erp)
"""

from datetime import date
from unittest.mock import patch

import pytest

from app.integrations.erp_models import ERPCustomer
from app.models import Customer
from app.services.erp_matching_service import (
    _create_customer_from_erp,
    _customer_has_changes,
    _match_customer_by_name,
    _normalize_name,
    _normalize_phone,
    _update_customer_fields,
    _validate_erp_customer_data,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _erp(
    erp_id: str = "ERP001",
    first_name: str = "Jean",
    last_name: str = "Dupont",
    **kwargs,
) -> ERPCustomer:
    return ERPCustomer(erp_id=erp_id, first_name=first_name, last_name=last_name, **kwargs)


def _customer(**kwargs) -> Customer:
    """Cree un Customer SQLAlchemy non-persiste pour les tests unitaires."""
    defaults = dict(
        tenant_id=1,
        first_name="Jean",
        last_name="Dupont",
        cosium_id=None,
        phone=None,
        email=None,
        address=None,
        city=None,
        postal_code=None,
        social_security_number=None,
        birth_date=None,
        customer_number=None,
        street_number=None,
        street_name=None,
        mobile_phone_country=None,
        site_id=None,
        optician_name=None,
        ophthalmologist_id=None,
        notes=None,
        avatar_url=None,
    )
    defaults.update(kwargs)
    return Customer(**defaults)


# ---------------------------------------------------------------------------
# _normalize_name
# ---------------------------------------------------------------------------


class TestNormalizeName:
    def test_removes_accents(self):
        assert _normalize_name("éàü") == "EAU"

    def test_uppercases(self):
        assert _normalize_name("jean dupont") == "JEAN DUPONT"

    def test_strips_whitespace(self):
        assert _normalize_name("  Jean  Dupont  ") == "JEAN DUPONT"

    def test_collapses_internal_spaces(self):
        assert _normalize_name("Jean   Dupont") == "JEAN DUPONT"

    def test_hyphens_become_spaces(self):
        assert _normalize_name("Marie-Claude") == "MARIE CLAUDE"

    def test_double_hyphens_become_single_space(self):
        assert _normalize_name("Dupont--Jean") == "DUPONT JEAN"

    def test_preserves_digits(self):
        assert _normalize_name("Dupont 2") == "DUPONT 2"

    def test_empty_string(self):
        assert _normalize_name("") == ""


# ---------------------------------------------------------------------------
# _normalize_phone
# ---------------------------------------------------------------------------


class TestNormalizePhone:
    def test_none_returns_none(self):
        assert _normalize_phone(None) is None

    def test_empty_string_returns_empty(self):
        assert _normalize_phone("") == ""

    def test_removes_spaces(self):
        assert _normalize_phone("06 12 34 56 78") == "0612345678"

    def test_removes_dots(self):
        assert _normalize_phone("06.12.34.56.78") == "0612345678"

    def test_removes_dashes(self):
        assert _normalize_phone("06-12-34-56-78") == "0612345678"

    def test_preserves_leading_plus(self):
        assert _normalize_phone("+33612345678") == "+33612345678"

    def test_preserves_leading_zero(self):
        assert _normalize_phone("0612345678") == "0612345678"

    def test_prepends_zero_when_no_prefix(self):
        assert _normalize_phone("612345678") == "0612345678"

    def test_international_format_no_leading_zero_added(self):
        # Commence par '+' -> pas de '0' ajoute
        result = _normalize_phone("+33 6 12 34 56 78")
        assert result.startswith("+")


# ---------------------------------------------------------------------------
# _match_customer_by_name
# ---------------------------------------------------------------------------


class TestMatchCustomerByName:
    def test_empty_name_returns_none(self):
        assert _match_customer_by_name("", {"JEAN DUPONT": 1}) is None

    def test_exact_match(self):
        name_map = {"JEAN DUPONT": 42}
        assert _match_customer_by_name("JEAN DUPONT", name_map) == 42

    def test_exact_match_case_insensitive(self):
        name_map = {"JEAN DUPONT": 7}
        assert _match_customer_by_name("jean dupont", name_map) == 7

    def test_exact_match_with_accents(self):
        name_map = {"DUPONT JEAN": 5}
        # Cosium envoie "Dupont Jéan" -> normalise en "DUPONT JEAN"
        assert _match_customer_by_name("Dupont Jéan", name_map) == 5

    def test_strip_m_prefix(self):
        name_map = {"DUPONT JEAN": 10}
        assert _match_customer_by_name("M. DUPONT JEAN", name_map) == 10

    def test_strip_mme_prefix(self):
        name_map = {"MARTIN SOPHIE": 11}
        assert _match_customer_by_name("Mme. MARTIN SOPHIE", name_map) == 11

    def test_strip_mme_no_dot_prefix(self):
        name_map = {"MARTIN SOPHIE": 12}
        assert _match_customer_by_name("MME MARTIN SOPHIE", name_map) == 12

    def test_strip_mlle_prefix(self):
        name_map = {"BERNARD ALICE": 13}
        assert _match_customer_by_name("MLLE. BERNARD ALICE", name_map) == 13

    def test_strip_dr_prefix(self):
        name_map = {"LEFORT PAUL": 99}
        assert _match_customer_by_name("DR. LEFORT PAUL", name_map) == 99

    def test_reverse_firstname_lastname(self):
        """Cosium: 'PRENOM NOM' dans name_map mais ERP envoie 'NOM PRENOM'."""
        name_map = {"JEAN DUPONT": 20}
        assert _match_customer_by_name("DUPONT JEAN", name_map) == 20

    def test_two_word_prefix_partial(self):
        """'RENGIG KULISKOVA LUBICA' doit matcher 'RENGIG KULISKOVA' (2 premiers mots)."""
        name_map = {"RENGIG KULISKOVA": 30}
        assert _match_customer_by_name("RENGIG KULISKOVA LUBICA", name_map) == 30

    def test_last_two_words_partial(self):
        """'RENGIG KULISKOVA LUBICA' doit matcher 'KULISKOVA LUBICA' (2 derniers mots)."""
        name_map = {"KULISKOVA LUBICA": 31}
        assert _match_customer_by_name("RENGIG KULISKOVA LUBICA", name_map) == 31

    def test_no_match_returns_none(self):
        name_map = {"JEAN DUPONT": 1, "SOPHIE MARTIN": 2}
        assert _match_customer_by_name("INCONNU TOTAL", name_map) is None

    def test_empty_map_returns_none(self):
        assert _match_customer_by_name("JEAN DUPONT", {}) is None

    def test_hyphen_normalized_before_match(self):
        """Traits d'union convertis en espaces avant la comparaison."""
        name_map = {"MARIE CLAUDE DUVAL": 40}
        assert _match_customer_by_name("Marie-Claude Duval", name_map) == 40

    def test_multiple_entries_first_exact_wins(self):
        """La correspondance exacte prend le dessus sur les autres."""
        name_map = {"JEAN DUPONT": 1, "DUPONT JEAN": 2}
        # "JEAN DUPONT" correspond directement
        result = _match_customer_by_name("JEAN DUPONT", name_map)
        assert result == 1

    def test_fuzzy_match_high_score(self):
        """Fuzzy matching : score >= 85 -> match retourne."""
        # "JEAN DUPOND" vs "JEAN DUPONT" : 1 caractere different -> score > 85
        name_map = {"JEAN DUPONT": 50}
        result = _match_customer_by_name("JEAN DUPOND", name_map)
        assert result == 50

    def test_fuzzy_match_low_score_returns_none(self):
        """Fuzzy matching : score < 85 -> None."""
        name_map = {"JEAN DUPONT": 50}
        # "ALICE TOTO" est tres different -> score < 85
        result = _match_customer_by_name("ALICE TOTO", name_map)
        assert result is None

    def test_fuzzy_best_score_wins(self):
        """Parmi plusieurs candidats fuzzy, le meilleur score gagne."""
        name_map = {
            "JEAN DUPONT": 10,
            "JEAN DUPONTI": 11,   # plus proche de "JEAN DUPONT" (score identique ou superieur)
        }
        result = _match_customer_by_name("JEAN DUPONT", name_map)
        # "JEAN DUPONT" est une correspondance exacte -> doit etre trouve avant le fuzzy
        assert result == 10

    def test_fuzzy_disabled_when_rapidfuzz_missing(self):
        """Si rapidfuzz n'est pas installe, aucune exception et retourne None."""
        name_map = {"JEAN DUPONT": 50}
        with patch.dict("sys.modules", {"rapidfuzz": None, "rapidfuzz.fuzz": None}):
            result = _match_customer_by_name("JEAN DUPOND", name_map)
        # Sans rapidfuzz le fuzzy est skippé -> None car pas de match exact
        assert result is None


# ---------------------------------------------------------------------------
# _validate_erp_customer_data
# ---------------------------------------------------------------------------


class TestValidateErpCustomerData:
    def test_valid_customer_no_warnings(self):
        c = _erp(
            email="jean@example.com",
            birth_date=date(1980, 1, 15),
            social_security_number="1 80 01 75 108 001 75",
        )
        warnings = _validate_erp_customer_data(c)
        assert warnings == []

    def test_invalid_email_generates_warning(self):
        c = _erp(email="not-an-email")
        warnings = _validate_erp_customer_data(c)
        assert any("Email invalide" in w for w in warnings)

    def test_future_birth_date_generates_warning(self):
        c = _erp(birth_date=date(2099, 1, 1))
        warnings = _validate_erp_customer_data(c)
        assert any("dans le futur" in w for w in warnings)

    def test_birth_date_before_1900_generates_warning(self):
        c = _erp(birth_date=date(1800, 6, 15))
        warnings = _validate_erp_customer_data(c)
        assert any("avant 1900" in w for w in warnings)

    def test_social_security_too_short_generates_warning(self):
        c = _erp(social_security_number="123456")  # 6 chiffres seulement
        warnings = _validate_erp_customer_data(c)
        assert any("securite sociale" in w for w in warnings)

    def test_social_security_too_long_generates_warning(self):
        c = _erp(social_security_number="1234567890123456")  # 16 chiffres
        warnings = _validate_erp_customer_data(c)
        assert any("securite sociale" in w for w in warnings)

    def test_valid_social_security_13_digits_no_warning(self):
        c = _erp(social_security_number="1234567890123")  # 13 chiffres -> valide
        warnings = _validate_erp_customer_data(c)
        assert not any("securite sociale" in w for w in warnings)

    def test_social_security_with_spaces_counts_only_digits(self):
        # "1 80 01 75 108 001 75" -> 15 chiffres -> valide
        c = _erp(social_security_number="1 80 01 75 108 001 75")
        warnings = _validate_erp_customer_data(c)
        assert not any("securite sociale" in w for w in warnings)

    def test_no_email_no_warning(self):
        c = _erp(email=None)
        warnings = _validate_erp_customer_data(c)
        assert warnings == []

    def test_multiple_warnings_can_be_returned(self):
        c = _erp(email="bad-email", birth_date=date(2099, 1, 1))
        warnings = _validate_erp_customer_data(c)
        assert len(warnings) >= 2


# ---------------------------------------------------------------------------
# _customer_has_changes
# ---------------------------------------------------------------------------


class TestCustomerHasChanges:
    def test_no_changes_returns_false(self):
        existing = _customer(
            cosium_id="ERP001",
            phone="0612345678",
            email="jean@example.com",
            first_name="Jean",
            last_name="Dupont",
        )
        erp_c = _erp(
            erp_id="ERP001",
            phone="0612345678",
            email="jean@example.com",
            first_name="Jean",
            last_name="Dupont",
        )
        assert _customer_has_changes(existing, erp_c) is False

    def test_missing_cosium_id_triggers_change(self):
        existing = _customer(cosium_id=None)
        erp_c = _erp(erp_id="ERP001")
        assert _customer_has_changes(existing, erp_c) is True

    def test_new_phone_triggers_change(self):
        existing = _customer(phone=None)
        erp_c = _erp(phone="0699000000")
        assert _customer_has_changes(existing, erp_c) is True

    def test_new_email_triggers_change(self):
        existing = _customer(email=None)
        erp_c = _erp(email="new@example.com")
        assert _customer_has_changes(existing, erp_c) is True

    def test_email_case_difference_triggers_change(self):
        existing = _customer(email="jean@example.com")
        erp_c = _erp(email="Jean@Example.com")
        # email different en casse -> changement
        assert _customer_has_changes(existing, erp_c) is True

    def test_same_email_different_case_no_change(self):
        # Meme email (normalise) -> pas de changement quand cosium_id est deja renseigne
        existing = _customer(email="jean@example.com", cosium_id="ERP001")
        erp_c = _erp(email="jean@example.com")
        assert _customer_has_changes(existing, erp_c) is False

    def test_first_name_difference_triggers_change(self):
        existing = _customer(first_name="Jean")
        erp_c = _erp(first_name="Pierre")
        assert _customer_has_changes(existing, erp_c) is True

    def test_last_name_difference_triggers_change(self):
        existing = _customer(last_name="Dupont")
        erp_c = _erp(last_name="Martin")
        assert _customer_has_changes(existing, erp_c) is True

    def test_new_birth_date_triggers_change(self):
        existing = _customer(birth_date=None)
        erp_c = _erp(birth_date=date(1990, 5, 10))
        assert _customer_has_changes(existing, erp_c) is True

    def test_new_site_id_triggers_change(self):
        existing = _customer(site_id=None)
        erp_c = _erp(site_id=7)
        assert _customer_has_changes(existing, erp_c) is True

    def test_erp_has_no_data_to_add_returns_false(self):
        """Si l'ERP n'apporte rien de nouveau, aucun changement detecte."""
        existing = _customer(
            cosium_id="ERP001",
            phone="0612345678",
            first_name="Jean",
            last_name="Dupont",
        )
        erp_c = _erp(
            erp_id="ERP001",
            first_name="Jean",
            last_name="Dupont",
            phone=None,  # ERP n'a pas le telephone
        )
        assert _customer_has_changes(existing, erp_c) is False


# ---------------------------------------------------------------------------
# _update_customer_fields
# ---------------------------------------------------------------------------


class TestUpdateCustomerFields:
    def test_sets_cosium_id_when_missing(self):
        existing = _customer(cosium_id=None)
        erp_c = _erp(erp_id="ERP999")
        changed = _update_customer_fields(existing, erp_c)
        assert changed is True
        assert existing.cosium_id == "ERP999"

    def test_does_not_overwrite_existing_cosium_id(self):
        existing = _customer(cosium_id="OLD-ID")
        erp_c = _erp(erp_id="NEW-ID")
        _update_customer_fields(existing, erp_c)
        assert existing.cosium_id == "OLD-ID"

    def test_fills_empty_phone(self):
        existing = _customer(phone=None)
        erp_c = _erp(phone="0600000000")
        changed = _update_customer_fields(existing, erp_c)
        assert changed is True
        assert existing.phone == "0600000000"

    def test_does_not_overwrite_existing_phone(self):
        existing = _customer(phone="0611111111", cosium_id="ERP001")
        erp_c = _erp(phone="0699999999")
        changed = _update_customer_fields(existing, erp_c)
        assert changed is False
        assert existing.phone == "0611111111"

    def test_fills_empty_city_and_postal_code(self):
        existing = _customer(city=None, postal_code=None)
        erp_c = _erp(city="Paris", postal_code="75001")
        _update_customer_fields(existing, erp_c)
        assert existing.city == "Paris"
        assert existing.postal_code == "75001"

    def test_fills_birth_date_when_missing(self):
        existing = _customer(birth_date=None)
        erp_c = _erp(birth_date=date(1985, 3, 22))
        changed = _update_customer_fields(existing, erp_c)
        assert changed is True
        assert existing.birth_date == date(1985, 3, 22)

    def test_does_not_overwrite_existing_birth_date(self):
        existing = _customer(birth_date=date(1985, 3, 22), cosium_id="ERP001")
        erp_c = _erp(birth_date=date(1990, 1, 1))
        changed = _update_customer_fields(existing, erp_c)
        assert changed is False

    def test_fills_site_id_when_missing(self):
        existing = _customer(site_id=None)
        erp_c = _erp(site_id=3)
        changed = _update_customer_fields(existing, erp_c)
        assert changed is True
        assert existing.site_id == 3

    def test_no_changes_returns_false(self):
        existing = _customer(cosium_id="ERP001", phone="0600000000")
        erp_c = _erp(erp_id="ERP001", phone="0600000000")
        changed = _update_customer_fields(existing, erp_c)
        assert changed is False

    def test_fills_multiple_fields_at_once(self):
        existing = _customer(cosium_id=None, phone=None, city=None)
        erp_c = _erp(erp_id="E1", phone="0612345678", city="Lyon")
        changed = _update_customer_fields(existing, erp_c)
        assert changed is True
        assert existing.cosium_id == "E1"
        assert existing.phone == "0612345678"
        assert existing.city == "Lyon"


# ---------------------------------------------------------------------------
# _create_customer_from_erp
# ---------------------------------------------------------------------------


class TestCreateCustomerFromErp:
    def test_creates_customer_with_correct_tenant(self):
        erp_c = _erp(erp_id="ERP100", first_name="Marie", last_name="Curie")
        customer = _create_customer_from_erp(tenant_id=5, erp_c=erp_c)
        assert customer.tenant_id == 5

    def test_sets_cosium_id(self):
        erp_c = _erp(erp_id="ERP101")
        customer = _create_customer_from_erp(1, erp_c)
        assert customer.cosium_id == "ERP101"

    def test_cosium_id_none_when_no_erp_id(self):
        erp_c = ERPCustomer(erp_id="", first_name="X", last_name="Y")
        customer = _create_customer_from_erp(1, erp_c)
        # erp_id vide -> falsy -> cosium_id None
        assert customer.cosium_id is None

    def test_maps_basic_fields(self):
        erp_c = _erp(
            erp_id="E1",
            first_name="Paul",
            last_name="Martin",
            email="paul@example.com",
            city="Bordeaux",
            postal_code="33000",
            address="1 rue de la Paix",
        )
        customer = _create_customer_from_erp(1, erp_c)
        assert customer.first_name == "Paul"
        assert customer.last_name == "Martin"
        assert customer.email == "paul@example.com"
        assert customer.city == "Bordeaux"
        assert customer.postal_code == "33000"
        assert customer.address == "1 rue de la Paix"

    def test_phone_is_normalized(self):
        erp_c = _erp(phone="06 12 34 56 78")
        customer = _create_customer_from_erp(1, erp_c)
        assert customer.phone == "0612345678"

    def test_phone_none_stays_none(self):
        erp_c = _erp(phone=None)
        customer = _create_customer_from_erp(1, erp_c)
        assert customer.phone is None

    def test_birth_date_mapped(self):
        erp_c = _erp(birth_date=date(1992, 7, 14))
        customer = _create_customer_from_erp(1, erp_c)
        assert customer.birth_date == date(1992, 7, 14)

    def test_site_id_mapped(self):
        erp_c = _erp(site_id=12)
        customer = _create_customer_from_erp(1, erp_c)
        assert customer.site_id == 12

    def test_data_quality_warnings_logged(self):
        """Les warnings de qualite sont logues sans bloquer la creation."""
        erp_c = _erp(email="not-an-email", birth_date=date(2099, 1, 1))
        with patch("app.services.erp_matching_service.logger") as mock_logger:
            customer = _create_customer_from_erp(1, erp_c)
        # Le client est quand meme cree
        assert customer is not None
        # Au moins 2 appels warning (email + date)
        assert mock_logger.warning.call_count >= 2

    def test_returns_customer_instance(self):
        erp_c = _erp()
        result = _create_customer_from_erp(1, erp_c)
        assert isinstance(result, Customer)
