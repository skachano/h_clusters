import "@testing-library/jest-dom/vitest";

// jsdom has no ResizeObserver; charts measure their width with it (charts/frame.ts useWidth).
globalThis.ResizeObserver ??= class {
  observe() {}
  unobserve() {}
  disconnect() {}
} as unknown as typeof ResizeObserver;
