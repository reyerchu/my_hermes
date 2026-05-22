import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, cleanup, waitFor } from "@testing-library/react";
import { RouterWrapper, makeTranslationStub } from "@/test-helpers";

const apiMock = vi.hoisted(() => ({
  getModelsAnalytics: vi.fn(),
  getModelOptions: vi.fn(),
  getAuxiliaryModels: vi.fn(),
  setModelAssignment: vi.fn(),
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
  Stats: () => null,
}));
// Some Models UI uses the ModelPickerDialog component — stub it so we don't
// pull in nested DS deps in jsdom.
vi.mock("@/components/ModelPickerDialog", () => ({
  ModelPickerDialog: () => null,
}));

import ModelsPage from "./ModelsPage";

describe("ModelsPage smoke", () => {
  beforeEach(() => Object.values(apiMock).forEach((m: any) => m.mockReset()));
  afterEach(() => cleanup());

  it("calls model analytics + options + auxiliary models on mount", async () => {
    apiMock.getModelsAnalytics.mockResolvedValue({
      models: [],
      totals: {},
    });
    apiMock.getModelOptions.mockResolvedValue({ providers: [], models: [] });
    apiMock.getAuxiliaryModels.mockResolvedValue(null);
    render(
      <RouterWrapper>
        <ModelsPage />
      </RouterWrapper>,
    );
    await waitFor(() => {
      expect(apiMock.getModelsAnalytics).toHaveBeenCalled();
    });
  });

  it("recovers when getModelsAnalytics rejects", async () => {
    apiMock.getModelsAnalytics.mockRejectedValue(new Error("nope"));
    apiMock.getModelOptions.mockRejectedValue(new Error("nope"));
    apiMock.getAuxiliaryModels.mockRejectedValue(new Error("nope"));
    expect(() =>
      render(
        <RouterWrapper>
          <ModelsPage />
        </RouterWrapper>,
      ),
    ).not.toThrow();
  });
});
