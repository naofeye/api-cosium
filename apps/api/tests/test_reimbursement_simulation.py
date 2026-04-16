"""Tests de la simulation de remboursement optique (heuristique)."""

from app.services.reimbursement_simulation_service import simulate_reimbursement


def test_simulation_classe_a_prend_tout_en_charge() -> None:
    res = simulate_reimbursement(
        prix_monture=150, prix_verre_od=200, prix_verre_og=200, classe_a=True
    )
    assert res["total_ttc"] == 550.0
    assert res["part_ss"] == 550.0
    assert res["reste_a_charge"] == 0.0


def test_simulation_myopie_simple_mutuelle_100pct() -> None:
    res = simulate_reimbursement(
        prix_monture=150,
        prix_verre_od=200,
        prix_verre_og=200,
        sphere_od=-2.0,
        sphere_og=-2.0,
        mutuelle_pct_verres=100,
        mutuelle_forfait_monture=100,
    )
    assert res["total_ttc"] == 550.0
    # Secu rembourse peu sur monture (0.03 * 0.60) + 60% de 7.32 pour chaque verre
    assert res["part_ss"] < 10
    # Mutuelle 100% couvre le reste des verres + forfait 100 EUR monture → reste > 0 (50 EUR)
    assert res["reste_a_charge"] > 0
    # Somme coherente
    assert abs(res["total_ttc"] - (res["part_ss"] + res["part_mutuelle"] + res["reste_a_charge"])) < 0.01


def test_simulation_verres_progressifs_complexes() -> None:
    """Sphere elevee + addition => BR tres complexe => SS plus elevee."""
    simple = simulate_reimbursement(
        prix_verre_od=300, prix_verre_og=300, sphere_od=-1, sphere_og=-1
    )
    complexe = simulate_reimbursement(
        prix_verre_od=300, prix_verre_og=300, sphere_od=-5, sphere_og=-5, addition_od=2, addition_og=2
    )
    assert complexe["part_ss"] > simple["part_ss"]


def test_simulation_mutuelle_nulle() -> None:
    res = simulate_reimbursement(
        prix_monture=100,
        prix_verre_od=50,
        prix_verre_og=50,
        sphere_od=-1,
        sphere_og=-1,
        mutuelle_pct_verres=0,
        mutuelle_forfait_monture=0,
    )
    # Sans mutuelle, le RAC doit etre proche de TTC (sauf petite part SS)
    assert res["part_mutuelle"] == 0.0
    assert res["reste_a_charge"] >= 180  # 200 - ~SS 10
