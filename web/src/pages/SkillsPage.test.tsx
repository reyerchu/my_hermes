import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, cleanup, waitFor } from "@testing-library/react";
import { RouterWrapper, makeTranslationStub } from "@/test-helpers";

const apiMock = vi.hoisted(() => ({
  getSkills: vi.fn(),
  getToolsets: vi.fn(),
  toggleSkill: vi.fn(),
}));
const headerStub = vi.hoisted(() => ({
  setTitle: vi.fn(),
  setAfterTitle: vi.fn(),
  setEnd: vi.fn(),
}));

vi.mock("@/lib/api", () => ({ api: apiMock }));
vi.mock("@/contexts/usePageHeader", () => ({
  usePageHeader: () => headerStub,
}));
// Shared recursive translation stub — SkillsPage reads ~30 keys plus
// template strings, so enumerating them per test is brittle.
vi.mock("@/i18n", () => ({
  useI18n: () => ({ t: makeTranslationStub() }),
}));
vi.mock("@/plugins", () => ({ PluginSlot: () => null }));
vi.mock("@nous-research/ui/ui/components/badge", () => ({
  Badge: ({ children }: any) => <span>{children}</span>,
}));
vi.mock("@nous-research/ui/ui/components/button", () => ({
  Button: ({ children, onClick, disabled }: any) => (
    <button onClick={onClick} disabled={disabled}>{children}</button>
  ),
}));
vi.mock("@nous-research/ui/ui/components/spinner", () => ({
  Spinner: () => <div data-testid="spinner" />,
}));
vi.mock("@nous-research/ui/ui/components/switch", () => ({
  Switch: ({ checked, onCheckedChange }: any) => (
    <input
      type="checkbox"
      role="switch"
      checked={checked}
      onChange={(e) => onCheckedChange?.(e.target.checked)}
    />
  ),
}));
vi.mock("@nous-research/ui/ui/components/list-item", () => ({
  ListItem: ({ children, onClick }: any) => (
    <div onClick={onClick} role="listitem">{children}</div>
  ),
}));

import SkillsPage from "./SkillsPage";

describe("SkillsPage smoke", () => {
  beforeEach(() => {
    apiMock.getSkills.mockReset();
    apiMock.getToolsets.mockReset();
    apiMock.toggleSkill.mockReset();
  });
  afterEach(() => cleanup());

  it("calls both api.getSkills and api.getToolsets on mount", async () => {
    apiMock.getSkills.mockResolvedValue([]);
    apiMock.getToolsets.mockResolvedValue([]);
    render(
      <RouterWrapper>
        <SkillsPage />
      </RouterWrapper>,
    );
    await waitFor(() => {
      expect(apiMock.getSkills).toHaveBeenCalled();
      expect(apiMock.getToolsets).toHaveBeenCalled();
    });
  });

  it("renders a skill name from the API response", async () => {
    const fixture = {
      id: "review",
      name: "review",
      description: "Review changes",
      category: "code",
      source: "builtin",
      enabled: true,
      profile: "default",
    };
    apiMock.getSkills.mockResolvedValue([fixture]);
    apiMock.getToolsets.mockResolvedValue([]);
    const { container } = render(
      <RouterWrapper>
        <SkillsPage />
      </RouterWrapper>,
    );
    await waitFor(() => expect(apiMock.getSkills).toHaveBeenCalled());
    await waitFor(() =>
      expect(container.textContent).toContain("review"),
    );
  });

  it("does not crash when both endpoints reject", async () => {
    apiMock.getSkills.mockRejectedValue(new Error("boom"));
    apiMock.getToolsets.mockRejectedValue(new Error("boom"));
    expect(() =>
      render(
        <RouterWrapper>
          <SkillsPage />
        </RouterWrapper>,
      ),
    ).not.toThrow();
    await waitFor(() => expect(apiMock.getSkills).toHaveBeenCalled());
  });
});
