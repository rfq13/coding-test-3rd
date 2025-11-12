import { describe, it, expect } from "vitest";
import { fundApi } from "@/lib/api";
import { rest } from "msw";
import { server } from "@/test/msw-server";

describe("fundApi.list", () => {
  it("returns list of funds on success", async () => {
    server.use(
      rest.get("/api/funds/", (_req, res, ctx) => {
        return res(
          ctx.json([
            { id: 1, name: "Alpha Fund" },
            { id: 2, name: "Beta Fund" },
          ])
        );
      })
    );

    const data = await fundApi.list();
    expect(Array.isArray(data)).toBe(true);
    expect(data[0].name).toBe("Alpha Fund");
  });

  it("returns clear error message on failure", async () => {
    server.use(
      rest.get("/api/funds/", (_req, res, ctx) => {
        return res(ctx.status(500), ctx.json({ detail: "Failed to load" }));
      })
    );

    await expect(fundApi.list()).rejects.toThrow(/500 Failed to load/);
  });
});
