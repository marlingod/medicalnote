import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { RegisterForm } from "./register-form";

vi.mock("@/lib/api-client", () => ({
  apiClient: { auth: { register: vi.fn() } },
}));
vi.mock("@/lib/auth-context", () => ({
  useAuth: () => ({ login: vi.fn(), isLoading: false }),
}));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

describe("RegisterForm", () => {
  it("renders all required registration fields", () => {
    render(<RegisterForm />);
    expect(screen.getByLabelText(/first name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/last name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/practice name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument();
  });

  it("renders a submit button", () => {
    render(<RegisterForm />);
    expect(screen.getByRole("button", { name: /create account/i })).toBeInTheDocument();
  });
});
