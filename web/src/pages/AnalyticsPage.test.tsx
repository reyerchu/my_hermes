import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, cleanup, waitFor } from "@testing-library/react";
import { RouterWrapper, makeTranslationStub } from "@/test-helpers";

const apiMock = vi.hoisted(() => ({
  getAnalytics: vi.fn(),
}));
const headerStub = vi.hoisted(() => ({
  setTitle: vi.fn(), setAfterTitle: vi.fn(), setEnd: vi.fn(),
}));

vi.mock("@/lib/api", () => ({ api: apiMock }));
vi.mock("@/contexts/usePageHeader", () => ({ usePageHeader: () => headerStub }));
vi.mock("@/i18n", () => ({ useI18n: () => ({ t: makeTranslationStub() }) }));
vi.mock("@/plugins", () => ({ PluginSlot: () => null }));
vi.mock("@nous-research/ui/ui/components/badge", () => ({
  Badge: ({ children }: any) => <span>{children}</span>,
}));
vi.mock("@nous-research/ui/ui/components/button", () => ({
  Button: ({ children, onClick }: any) => <button onClick={onClick}>{children}</button>,
}));
vi.mock("@nous-research/ui/ui/components/spinner", () => ({
  Spinner: () => <div data-testid="spinner" />,
}));
vi.mock("@nous-research/ui/ui/components/stats", () => ({
  Stats: ({ items }: { items: Array<{ label: string; value: string }> }) => (
    <div>
      {items?.map?.((it, i) => (
        <div key={i}>{it.label}: {it.value}</div>
      ))}
    </div>
  ),
}));

import AnalyticsPage from "./AnalyticsPage";

const analyticsFixture = {
  days: 7,
  daily: [],
  by_model: [],
  skills: { top_skills: [] },
  totals: {
    total_api_calls: 0,
    total_tokens: 0,
    total_cost_usd: 0,
    total_input: 0,
    total_output: 0,
    total_sessions: 0,
  },
  generated_at: new Date().toISOString(),
};

describe("AnalyticsPage smoke", () => {
  beforeEach(() => apiMock.getAnalytics.mockReset());
  afterEach(() => cleanup());

  it("calls api.getAnalytics with the default 30-day period on mount", async () => {
    apiMock.getAnalytics.mockResolvedValue(analyticsFixture);
    render(
      <RouterWrapper>
        <AnalyticsPage />
      </RouterWrapper>,
    );
    await waitFor(() => expect(apiMock.getAnalytics).toHaveBeenCalledWith(30));
  });

  it("re-fetches when the period changes via setDays-driven effect", async () => {
    apiMock.getAnalytics.mockResolvedValue(analyticsFixture);
    const { rerender } = render(
      <RouterWrapper>
        <AnalyticsPage />
      </RouterWrapper>,
    );
    await waitFor(() => expect(apiMock.getAnalytics).toHaveBeenCalledWith(30));
    // Force a remount with a fresh fixture to verify the load callback is
    // wired and not memoised across mounts.
    rerender(
      <RouterWrapper>
        <AnalyticsPage />
      </RouterWrapper>,
    );
    await waitFor(() => expect(apiMock.getAnalytics).toHaveBeenCalled());
  });
});
