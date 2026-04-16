"""Simulation simple de remboursement optique : Securite Sociale + Mutuelle.

Utilise les regles RO 2024 indicatives :
- Monture : 0.03 EUR base SS (oui, 3 centimes officiels) — en pratique rien.
- Verres : par classe A (100% sante) rembourse integralement ; classe B libre.
- Les mutuelles remboursent un pourcentage du ticket moderateur ou un forfait.

Cette fonction est volontairement SIMPLE (heuristique) pour donner un ordre de grandeur
au client, pas une decompte exact. Elle doit etre remplacee par une table
`mutuelle_remboursement_rules` structuree pour un calcul precis.
"""
from __future__ import annotations

from decimal import Decimal

# Base de remboursement Securite Sociale (BR) - valeurs indicatives 2024
# Adultes simple foyer (>18 ans, verres simples)
SS_BASE_MONTURE = Decimal("0.03")
SS_BASE_VERRE_SIMPLE = Decimal("7.32")
SS_BASE_VERRE_COMPLEXE = Decimal("15.24")
SS_BASE_VERRE_TRES_COMPLEXE = Decimal("22.87")
SS_TAUX = Decimal("0.60")  # Secu rembourse 60% de la BR


def _base_verre(sphere: float | None, cylindre: float | None, addition: float | None) -> Decimal:
    """Determine la BR selon la complexite optique."""
    sph = abs(sphere or 0)
    cyl = abs(cylindre or 0)
    add = addition or 0
    if add and add > 0:
        return SS_BASE_VERRE_TRES_COMPLEXE if sph >= 4 or cyl >= 2 else SS_BASE_VERRE_COMPLEXE
    if sph >= 6 or cyl >= 4:
        return SS_BASE_VERRE_COMPLEXE
    return SS_BASE_VERRE_SIMPLE


def simulate_reimbursement(
    *,
    prix_monture: float = 0.0,
    prix_verre_od: float = 0.0,
    prix_verre_og: float = 0.0,
    sphere_od: float | None = None,
    cylindre_od: float | None = None,
    addition_od: float | None = None,
    sphere_og: float | None = None,
    cylindre_og: float | None = None,
    addition_og: float | None = None,
    mutuelle_pct_verres: float = 100.0,  # % du TM ou forfait simplifie
    mutuelle_forfait_monture: float = 100.0,  # EUR
    classe_a: bool = False,
) -> dict:
    """Simule le remboursement pour un equipement complet lunettes.

    classe_a=True = equipement 100% sante (prise en charge integrale).
    Sinon calcul SS 60% * BR + mutuelle (pct verres / forfait monture).
    """
    total_ttc = Decimal(str(prix_monture + prix_verre_od + prix_verre_og))

    if classe_a:
        return {
            "total_ttc": float(total_ttc),
            "part_ss": float(total_ttc),
            "part_mutuelle": 0.0,
            "reste_a_charge": 0.0,
            "details": {"classe_a": True},
        }

    br_od = _base_verre(sphere_od, cylindre_od, addition_od)
    br_og = _base_verre(sphere_og, cylindre_og, addition_og)

    # Secu
    ss_monture = SS_BASE_MONTURE * SS_TAUX
    ss_verre_od = br_od * SS_TAUX
    ss_verre_og = br_og * SS_TAUX
    part_ss = ss_monture + ss_verre_od + ss_verre_og

    # Mutuelle : pct des verres (sans depasser le reste apres SS) + forfait monture plafonne
    reste_apres_ss_verres = Decimal(str(prix_verre_od + prix_verre_og)) - (ss_verre_od + ss_verre_og)
    part_mutuelle_verres = min(
        reste_apres_ss_verres,
        reste_apres_ss_verres * Decimal(str(mutuelle_pct_verres)) / Decimal("100"),
    )
    part_mutuelle_monture = min(
        Decimal(str(prix_monture)) - ss_monture,
        Decimal(str(mutuelle_forfait_monture)),
    )
    part_mutuelle = max(Decimal("0"), part_mutuelle_verres + part_mutuelle_monture)

    rac = max(Decimal("0"), total_ttc - part_ss - part_mutuelle)

    return {
        "total_ttc": float(total_ttc.quantize(Decimal("0.01"))),
        "part_ss": float(part_ss.quantize(Decimal("0.01"))),
        "part_mutuelle": float(part_mutuelle.quantize(Decimal("0.01"))),
        "reste_a_charge": float(rac.quantize(Decimal("0.01"))),
        "details": {
            "br_od": float(br_od),
            "br_og": float(br_og),
            "ss_monture": float(ss_monture.quantize(Decimal("0.01"))),
            "ss_verres": float((ss_verre_od + ss_verre_og).quantize(Decimal("0.01"))),
            "mutuelle_monture": float(part_mutuelle_monture.quantize(Decimal("0.01"))),
            "mutuelle_verres": float(part_mutuelle_verres.quantize(Decimal("0.01"))),
        },
    }
