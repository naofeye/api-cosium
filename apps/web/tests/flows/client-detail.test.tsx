import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, replace: vi.fn(), prefetch: vi.fn() }),
  useParams: () => ({ id: "42" }),
}));

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("@/components/ui/Toast", () => ({
  useToast: () => ({ toast: vi.fn() }),
}));

vi.mock("@/lib/api", () => ({
  fetchJson: vi.fn(),
}));

vi.mock("@/lib/download", () => ({
  downloadPdf: vi.fn(),
}));

vi.mock("@/components/layout/GlobalSearch", () => ({
  GlobalSearch: () => <div data-testid="global-search-mock" />,
}));

const mockMutate = vi.fn();

// Default mock data for a full client
const mockClient360 = {
  id: 42,
  first_name: "Marie",
  last_name: "Dupont",
  email: "marie@test.com",
  phone: "0612345678",
  birth_date: "1985-03-15",
  address: "12 rue de Paris",
  city: "Lyon",
  postal_code: "69001",
  social_security_number: "1850375069001",
  avatar_url: null,
  cosium_id: "12345",
  created_at: "2026-01-01T00:00:00",
  dossiers: [{ id: 1, statut: "en_cours", source: "manual", created_at: "2026-01-01" }],
  devis: [],
  factures: [{ id: 1, numero: "F-001", statut: "payee", montant_ttc: 500, date_emission: "2026-01-15" }],
  paiements: [],
  documents: [{ id: 1, type: "ordonnance", filename: "ordo.pdf", uploaded_at: "2026-01-01" }],
  pec: [],
  consentements: [{ canal: "email", consenti: true }],
  interactions: [
    { id: 1, type: "note", direction: "interne", subject: "Appel client", content: "RAS", created_at: "2026-01-10" },
  ],
  cosium_invoices: [],
  cosium_data: {
    prescriptions: [
      {
        id: 1,
        cosium_id: 100,
        prescription_date: "2025-06-01",
        prescriber_name: "Dr Martin",
        sphere_right: -2.5,
        cylinder_right: -0.75,
        axis_right: 90,
        addition_right: null,
        sphere_left: -3.0,
        cylinder_left: -0.5,
        axis_left: 85,
        addition_left: null,
        spectacles_json: null,
      },
    ],
    cosium_payments: [],
    calendar_events: [],
    equipments: [],
    correction_actuelle: {
      prescription_date: "2025-06-01",
      prescriber_name: "Dr Martin",
      sphere_right: -2.5,
      cylinder_right: -0.75,
      axis_right: 90,
      addition_right: null,
      sphere_left: -3.0,
      cylinder_left: -0.5,
      axis_left: 85,
      addition_left: null,
    },
    total_ca_cosium: 1500,
    last_visit_date: "2025-12-15",
    customer_tags: ["VIP"],
  },
  resume_financier: {
    total_facture: 500,
    total_paye: 500,
    reste_du: 0,
    taux_recouvrement: 100,
  },
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyClient = any;

// SWR mock — controlled per test
let swrReturnValue: { data: AnyClient | undefined; error: Error | undefined; isLoading: boolean; mutate: typeof mockMutate };

vi.mock("swr", () => ({
  default: () => swrReturnValue,
}));

import ClientDetailPage from "@/app/clients/[id]/page";

describe("Client Detail Flow - E2E style", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    swrReturnValue = {
      data: mockClient360,
      error: undefined,
      isLoading: false,
      mutate: mockMutate,
    };
  });

  it("renders loading state initially", () => {
    swrReturnValue = {
      data: undefined,
      error: undefined,
      isLoading: true,
      mutate: mockMutate,
    };
    render(<ClientDetailPage />);
    expect(screen.getByText("Chargement du client...")).toBeInTheDocument();
  });

  it("shows client name and tab navigation", () => {
    render(<ClientDetailPage />);
    // Client name appears (in title and avatar area)
    expect(screen.getAllByText("Marie Dupont").length).toBeGreaterThanOrEqual(1);
    // Tabs visible
    expect(screen.getByRole("tab", { name: /Resume/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Dossiers/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Finances/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Documents/i })).toBeInTheDocument();
  });

  it("switches tabs when clicking on a different tab", async () => {
    const user = userEvent.setup();
    render(<ClientDetailPage />);

    // Default tab is "Resume"
    const dossiersTab = screen.getByRole("tab", { name: /Dossiers/i });
    await user.click(dossiersTab);

    // After clicking Dossiers, it should be selected
    expect(dossiersTab).toHaveAttribute("aria-selected", "true");
  });

  it("shows correction data when cosium_data is present", () => {
    render(<ClientDetailPage />);
    // Should show Cosium badge
    expect(screen.getByText(/Cosium #12345/)).toBeInTheDocument();
    // Should show correction details (may appear in header and resume tab)
    expect(screen.getAllByText(/Correction/).length).toBeGreaterThanOrEqual(1);
    // Should show VIP tag
    expect(screen.getByText("VIP")).toBeInTheDocument();
  });

  it("renders gracefully when cosium_data is absent", () => {
    swrReturnValue = {
      data: {
        ...mockClient360,
        cosium_id: null,
        cosium_data: null,
      },
      error: undefined,
      isLoading: false,
      mutate: mockMutate,
    };
    render(<ClientDetailPage />);
    // Client name still shows
    expect(screen.getAllByText("Marie Dupont").length).toBeGreaterThanOrEqual(1);
    // No Cosium badge
    expect(screen.queryByText(/Cosium #/)).not.toBeInTheDocument();
    // Tabs still render
    expect(screen.getByRole("tab", { name: /Resume/i })).toBeInTheDocument();
  });
});
