import { describe, it, expect } from "vitest";
import { fundApi } from "@/lib/api";
import { http, HttpResponse } from "msw";
import { server } from "@/test/msw-server";

describe("fundApi.list", () => {
  it("returns list of funds on success", async () => {
    server.use(
      http.get("/api/funds/", (_req) => {
        return HttpResponse.json([
          { id: 1, name: "Alpha Fund" },
          { id: 2, name: "Beta Fund" },
        ]);
      })
    );

    const data = await fundApi.list();
    expect(Array.isArray(data)).toBe(true);
    expect(data[0].name).toBe("Alpha Fund");
  });

  it("returns clear error message on failure", async () => {
    server.use(
      http.get("/api/funds/", (_req) => {
        return HttpResponse.json({ detail: "Failed to load" }, { status: 500 });
      })
    );

    await expect(fundApi.list()).rejects.toThrow(/500 Failed to load/);
  });
});
