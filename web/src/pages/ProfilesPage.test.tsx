import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, cleanup, waitFor } from "@testing-library/react";
import { RouterWrapper } from "@/test-helpers";

const apiMock = vi.hoisted(() => ({
  getProfiles: vi.fn(),
  createProfile: vi.fn(),
  deleteProfile: vi.fn(),
  renameProfile: vi.fn(),
  getProfileSoul: vi.fn(),
  updateProfileSoul: vi.fn(),
  getProfileSetupCommand: vi.fn(),
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
        create: "Create",
        creating: "Creating",
        delete: "Delete",
        save: "Save",
        saving: "Saving",
      },
      status: { error: "Error" },
      profiles: {
        allProfiles: "All profiles",
        cloneFromDefault: "Clone from default",
        commandCopied: "Copied",
        confirmDeleteMessage: "Delete {name}?",
        confirmDeleteTitle: "Delete profile",
        copyFailed: "Copy failed",
        created: "Created",
        defaultBadge: "default",
        deleted: "Deleted",
        editSoul: "Edit soul",
        hasEnv: "Has env",
        invalidName: "Invalid name",
        model: "Model",
        name: "Name",
        namePlaceholder: "my-profile",
        nameRequired: "Name required",
        nameRule: "alphanumeric only",
        newProfile: "New profile",
        noProfiles: "No profiles yet",
        openInTerminal: "Open in terminal",
        rename: "Rename",
        renamed: "Renamed",
        saveSoul: "Save soul",
        skills: "Skills",
        soulPlaceholder: "Describe this profile…",
        soulSaved: "Saved",
        soulSection: "Soul",
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
vi.mock("@nous-research/ui/ui/components/list-item", () => ({
  ListItem: ({ children, onClick }: any) => (
    <div onClick={onClick} role="listitem">{children}</div>
  ),
}));
vi.mock("@nous-research/ui/ui/components/spinner", () => ({
  Spinner: () => <div data-testid="spinner" />,
}));
vi.mock("@nous-research/ui/ui/components/checkbox", () => ({
  Checkbox: (props: any) => <input type="checkbox" {...props} />,
}));

import ProfilesPage from "./ProfilesPage";

const profile = {
  name: "default",
  is_default: true,
  has_env: false,
  model: "claude-sonnet-4-6",
  skills: 3,
};

describe("ProfilesPage smoke", () => {
  beforeEach(() => {
    apiMock.getProfiles.mockReset();
    headerStub.setEnd.mockClear();
  });
  afterEach(() => cleanup());

  it("calls api.getProfiles on mount", async () => {
    apiMock.getProfiles.mockResolvedValue({ profiles: [] });
    render(
      <RouterWrapper>
        <ProfilesPage />
      </RouterWrapper>,
    );
    await waitFor(() => expect(apiMock.getProfiles).toHaveBeenCalledOnce());
  });

  it("renders a profile row from the API response", async () => {
    apiMock.getProfiles.mockResolvedValue({ profiles: [profile] });
    const { container } = render(
      <RouterWrapper>
        <ProfilesPage />
      </RouterWrapper>,
    );
    await waitFor(() => expect(apiMock.getProfiles).toHaveBeenCalled());
    // The profile name must appear somewhere in the rendered output once
    // the load promise resolves.
    await waitFor(() =>
      expect(container.textContent).toContain(profile.name),
    );
  });

  it("does not crash on an empty profile list", async () => {
    apiMock.getProfiles.mockResolvedValue({ profiles: [] });
    expect(() =>
      render(
        <RouterWrapper>
          <ProfilesPage />
        </RouterWrapper>,
      ),
    ).not.toThrow();
    await waitFor(() => expect(apiMock.getProfiles).toHaveBeenCalled());
  });

  it("recovers when getProfiles rejects (no unhandled exception)", async () => {
    apiMock.getProfiles.mockRejectedValue(new Error("boom"));
    expect(() =>
      render(
        <RouterWrapper>
          <ProfilesPage />
        </RouterWrapper>,
      ),
    ).not.toThrow();
    await waitFor(() => expect(apiMock.getProfiles).toHaveBeenCalled());
  });
});
