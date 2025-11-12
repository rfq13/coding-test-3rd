import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import CompareFundsPage from "@/app/funds/compare/page";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import { server } from "@/test/msw-server";

function renderWithQuery(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  );
}

describe("CompareFundsPage", () => {
  it("shows error state and Retry button when fetch fails", async () => {
    server.use(
      http.get("/api/funds/", (_req) => {
        return HttpResponse.json({ detail: "Service down" }, { status: 500 });
      })
    );

    renderWithQuery(<CompareFundsPage />);

    // Tunggu error muncul
    await waitFor(() => {
      expect(
        screen.getByText(/Error loading funds: 500 Service down/i)
      ).toBeInTheDocument();
    });

    // Tombol Retry tersedia
    const retryBtn = screen.getByRole("button", { name: /retry/i });
    expect(retryBtn).toBeInTheDocument();
  });

  it("shows fund list after Retry button click when fetch succeeds", async () => {
    server.use(
      http.get("/api/funds/", (_req) => {
        return HttpResponse.json({ detail: "Service down" }, { status: 500 });
      })
    );

    renderWithQuery(<CompareFundsPage />);

    await waitFor(() => {
      expect(
        screen.getByText(/Error loading funds: 500 Service down/i)
      ).toBeInTheDocument();
    });

    // Change handler: success
    server.use(
      http.get("/api/funds/", (_req) => {
        return HttpResponse.json([
            { id: 1, name: "Alpha Fund", fund_type: "VC", vintage_year: 2020 },
            { id: 2, name: "Beta Fund", fund_type: "PE", vintage_year: 2019 },
          ])
      })
    );

    // Click Retry
    const retryBtn = screen.getByRole("button", { name: /retry/i });
    await userEvent.click(retryBtn);

    // Ensure fund list appears
    await waitFor(() => {
      expect(screen.getByText("Alpha Fund")).toBeInTheDocument();
      expect(screen.getByText("Beta Fund")).toBeInTheDocument();
    });
  });

  it("shows empty state when fund list is empty", async () => {
    server.use(
      http.get("/api/funds/", (_req) => {
        return HttpResponse.json([]);
      })
    );

    renderWithQuery(<CompareFundsPage />);

    await waitFor(() => {
      expect(screen.getByText(/No funds found/i)).toBeInTheDocument();
    });
  });
});
