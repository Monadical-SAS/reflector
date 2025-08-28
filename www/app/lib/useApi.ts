// Compatibility layer for direct API client usage
// Prefer using React Query hooks from api-hooks.ts instead

import { client } from "./apiClient";

// Returns the configured client for direct API calls
// This is a minimal compatibility layer for components that haven't been fully migrated
export default function useApi() {
  return client;
}

// Export the client directly for non-hook contexts
export { client };
