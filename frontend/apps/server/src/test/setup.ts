import { afterEach, beforeEach, vi } from "vitest";

// Reset modules before each test
beforeEach(() => {
	vi.clearAllMocks();
});

// Cleanup after each test
afterEach(() => {
	vi.resetAllMocks();
});
