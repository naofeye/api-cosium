import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { KPICard } from "@/components/ui/KPICard";
import { Euro } from "lucide-react";

describe("KPICard", () => {
  it("affiche le label et la valeur", () => {
    render(<KPICard icon={Euro} label="CA total" value="1 234 €" />);
    expect(screen.getByText("CA total")).toBeInTheDocument();
    expect(screen.getByText("1 234 €")).toBeInTheDocument();
  });

  it("affiche l'icone", () => {
    const { container } = render(<KPICard icon={Euro} label="Test" value="100" />);
    const svg = container.querySelector("svg");
    expect(svg).toBeTruthy();
  });

  it("applique la classe couleur correspondante", () => {
    const { container: c1 } = render(<KPICard icon={Euro} label="A" value="1" color="success" />);
    expect(c1.firstElementChild!.className).toContain("border-t-success");

    const { container: c2 } = render(<KPICard icon={Euro} label="B" value="2" color="danger" />);
    expect(c2.firstElementChild!.className).toContain("border-t-danger");

    const { container: c3 } = render(<KPICard icon={Euro} label="C" value="3" color="primary" />);
    expect(c3.firstElementChild!.className).toContain("border-t-primary");
  });

  it("affiche l'indicateur de tendance si fourni", () => {
    render(<KPICard icon={Euro} label="Tendance" value="500" trend={{ value: 12 }} />);
    expect(screen.getByText("+12%")).toBeInTheDocument();

    const { unmount } = render(<KPICard icon={Euro} label="Baisse" value="300" trend={{ value: -5 }} />);
    expect(screen.getByText("-5%")).toBeInTheDocument();
    unmount();
  });
});
