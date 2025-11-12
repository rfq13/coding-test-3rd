import { setupServer } from "msw/node";

// Global MSW server; handlers will be set per test via server.use()
export const server = setupServer();
