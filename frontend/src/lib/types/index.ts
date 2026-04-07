// Barrel re-export — all types accessible via "@/lib/types"
export * from "./batch";
export * from "./client";
export * from "./cosium";
export * from "./financial";
export * from "./pec-preparation";

// --- Generic API ---
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface ApiError {
  error: {
    code: string;
    message: string;
    field?: string;
  };
}
