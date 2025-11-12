import "@testing-library/jest-dom";
import { server } from "./test/msw-server";

// MSW server lifecycle hooks
beforeAll(() => {
  server.listen({ onUnhandledRequest: "error" });
});

afterEach(() => {
  server.resetHandlers();
});

afterAll(() => {
  server.close();
});
