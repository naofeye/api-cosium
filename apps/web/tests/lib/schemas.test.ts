import { describe, it, expect } from "vitest";
import { loginSchema } from "@/lib/schemas/auth";
import { clientCreateSchema } from "@/lib/schemas/client";
import { caseCreateSchema } from "@/lib/schemas/case";
import { devisLineSchema } from "@/lib/schemas/devis";
import { signupSchema } from "@/lib/schemas/onboarding";
import { campaignCreateSchema } from "@/lib/schemas/marketing";

describe("loginSchema", () => {
  it("rejette un email vide", () => {
    const result = loginSchema.safeParse({ email: "", password: "test" });
    expect(result.success).toBe(false);
  });

  it("rejette un email invalide", () => {
    const result = loginSchema.safeParse({ email: "pasunemail", password: "test" });
    expect(result.success).toBe(false);
  });

  it("accepte des identifiants valides", () => {
    const result = loginSchema.safeParse({ email: "test@test.com", password: "monpassword" });
    expect(result.success).toBe(true);
  });
});

describe("clientCreateSchema", () => {
  it("rejette un nom vide", () => {
    const result = clientCreateSchema.safeParse({ first_name: "Jean", last_name: "" });
    expect(result.success).toBe(false);
  });

  it("rejette un email invalide", () => {
    const result = clientCreateSchema.safeParse({ first_name: "Jean", last_name: "Dupont", email: "bad" });
    expect(result.success).toBe(false);
  });

  it("accepte un client avec nom et prenom", () => {
    const result = clientCreateSchema.safeParse({ first_name: "Jean", last_name: "Dupont" });
    expect(result.success).toBe(true);
  });

  it("accepte un client complet", () => {
    const result = clientCreateSchema.safeParse({
      first_name: "Jean",
      last_name: "Dupont",
      email: "jean@test.com",
      phone: "0612345678",
      city: "Paris",
    });
    expect(result.success).toBe(true);
  });
});

describe("caseCreateSchema", () => {
  it("rejette un prenom vide", () => {
    const result = caseCreateSchema.safeParse({ first_name: "", last_name: "Test", source: "manual" });
    expect(result.success).toBe(false);
  });

  it("accepte un dossier complet", () => {
    const result = caseCreateSchema.safeParse({ first_name: "Jean", last_name: "Test", source: "manual" });
    expect(result.success).toBe(true);
  });
});

describe("devisLineSchema", () => {
  it("rejette une quantite negative", () => {
    const result = devisLineSchema.safeParse({ designation: "Test", quantite: -1, prix_unitaire_ht: 100, taux_tva: 20 });
    expect(result.success).toBe(false);
  });

  it("rejette un prix negatif", () => {
    const result = devisLineSchema.safeParse({ designation: "Test", quantite: 1, prix_unitaire_ht: -50, taux_tva: 20 });
    expect(result.success).toBe(false);
  });

  it("accepte une ligne valide", () => {
    const result = devisLineSchema.safeParse({ designation: "Monture", quantite: 1, prix_unitaire_ht: 180, taux_tva: 20 });
    expect(result.success).toBe(true);
  });
});

describe("signupSchema", () => {
  it("rejette un mot de passe sans majuscule", () => {
    const result = signupSchema.safeParse({
      company_name: "Test",
      owner_email: "a@b.com",
      owner_password: "password1",
      owner_first_name: "Jean",
      owner_last_name: "Test",
    });
    expect(result.success).toBe(false);
  });

  it("rejette un mot de passe sans chiffre", () => {
    const result = signupSchema.safeParse({
      company_name: "Test",
      owner_email: "a@b.com",
      owner_password: "Password",
      owner_first_name: "Jean",
      owner_last_name: "Test",
    });
    expect(result.success).toBe(false);
  });

  it("accepte un signup valide", () => {
    const result = signupSchema.safeParse({
      company_name: "Optique Test",
      owner_email: "test@test.com",
      owner_password: "Password1",
      owner_first_name: "Jean",
      owner_last_name: "Test",
    });
    expect(result.success).toBe(true);
  });
});

describe("campaignCreateSchema", () => {
  it("rejette un nom vide", () => {
    const result = campaignCreateSchema.safeParse({ name: "", segment_id: 1, channel: "email", template: "Hello" });
    expect(result.success).toBe(false);
  });

  it("rejette un channel invalide", () => {
    const result = campaignCreateSchema.safeParse({ name: "Test", segment_id: 1, channel: "fax", template: "Hello" });
    expect(result.success).toBe(false);
  });

  it("accepte une campagne email valide", () => {
    const result = campaignCreateSchema.safeParse({
      name: "Campagne test",
      segment_id: 1,
      channel: "email",
      template: "Bonjour {{client_name}}",
    });
    expect(result.success).toBe(true);
  });
});
