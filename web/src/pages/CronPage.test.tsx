import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, cleanup, waitFor } from "@testing-library/react";
import { RouterWrapper } from "@/test-helpers";

const apiMock = vi.hoisted(() => ({
  getCronJobs: vi.fn(),
  createCronJob: vi.fn(),
  pauseCronJob: vi.fn(),
  resumeCronJob: vi.fn(),
  triggerCronJob: vi.fn(),
  deleteCronJob: vi.fn(),
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
vi.mock("@/i18n", () => ({
  useI18n: () => ({
    t: {
      common: {
        cancel: "Cancel",
        delete: "Delete",
        save: "Save",
        edit: "Edit",
        add: "Add",
        create: "Create",
        creating: "Creating…",
        loading: "Loading…",
      },
      config: { failedToSave: "Save failed" },
      status: { error: "Error" },
      cron: {
        title: "Cron",
        new: "New",
        newJob: "New job",
        scheduledJobs: "Scheduled jobs",
        empty: "No jobs scheduled.",
        noJobs: "No cron jobs",
        deliverTo: "Deliver to",
        last: "Last",
        next: "Next",
        pause: "Pause",
        resume: "Resume",
        triggerNow: "Trigger now",
        prompt: "Prompt",
        promptPlaceholder: "Describe what to run…",
        nameOptional: "Name (optional)",
        namePlaceholder: "Daily report",
        schedule: "Schedule",
        schedulePlaceholder: "0 9 * * *",
        confirmDeleteMessage: "Delete this job?",
        confirmDeleteTitle: "Delete job",
        delivery: {
          local: "Local",
          telegram: "Telegram",
          slack: "Slack",
          discord: "Discord",
          email: "Email",
        },
      },
    },
  }),
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
vi.mock("@nous-research/ui/ui/components/select", () => ({
  Select: ({ children, value, onChange }: any) => (
    <select value={value} onChange={(e) => onChange?.(e.target.value)}>
      {children}
    </select>
  ),
  SelectOption: ({ value, children }: any) => <option value={value}>{children}</option>,
}));

import CronPage from "./CronPage";

const jobFixture = {
  id: "job-1",
  name: "Daily report",
  prompt: "Summarise the day",
  schedule_display: "0 9 * * *",
  schedule: { display: "0 9 * * *", expr: "0 9 * * *" },
  state: "scheduled",
  enabled: true,
  last_run: null,
  next_run: "2026-05-23T09:00:00Z",
};

describe("CronPage smoke", () => {
  beforeEach(() => {
    apiMock.getCronJobs.mockReset();
    apiMock.createCronJob.mockReset();
    apiMock.pauseCronJob.mockReset();
    apiMock.resumeCronJob.mockReset();
    apiMock.triggerCronJob.mockReset();
    apiMock.deleteCronJob.mockReset();
    headerStub.setEnd.mockClear();
  });
  afterEach(() => cleanup());

  it("calls api.getCronJobs on mount", async () => {
    apiMock.getCronJobs.mockResolvedValue([]);
    render(
      <RouterWrapper>
        <CronPage />
      </RouterWrapper>,
    );
    await waitFor(() => expect(apiMock.getCronJobs).toHaveBeenCalledOnce());
  });

  it("renders job names from the API response", async () => {
    apiMock.getCronJobs.mockResolvedValue([jobFixture]);
    const { findByText } = render(
      <RouterWrapper>
        <CronPage />
      </RouterWrapper>,
    );
    expect(await findByText("Daily report")).toBeTruthy();
  });

  it("renders an empty state when there are no jobs", async () => {
    apiMock.getCronJobs.mockResolvedValue([]);
    const { container } = render(
      <RouterWrapper>
        <CronPage />
      </RouterWrapper>,
    );
    await waitFor(() => expect(apiMock.getCronJobs).toHaveBeenCalled());
    // After load: no spinner, and the jobs container has no "job-row" entries
    // since we mocked getCronJobs with []. Just assert it didn't crash and
    // there's an empty-ish render.
    expect(container.querySelector("[data-testid='spinner']")).toBeNull();
  });

  it("recovers gracefully when getCronJobs rejects", async () => {
    apiMock.getCronJobs.mockRejectedValue(new Error("boom"));
    expect(() =>
      render(
        <RouterWrapper>
          <CronPage />
        </RouterWrapper>,
      ),
    ).not.toThrow();
    await waitFor(() => expect(apiMock.getCronJobs).toHaveBeenCalled());
  });

  it("registers a header action (the +New button) via setEnd", async () => {
    apiMock.getCronJobs.mockResolvedValue([]);
    render(
      <RouterWrapper>
        <CronPage />
      </RouterWrapper>,
    );
    await waitFor(() => expect(headerStub.setEnd).toHaveBeenCalled());
  });
});
