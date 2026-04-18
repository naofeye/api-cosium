import useSWR from "swr";

// --- IA endpoints ---
export function usePreRdvBrief(customerId: number | string | null) {
  return useSWR(customerId ? `/ai/client/${customerId}/pre-rdv-brief` : null);
}

export function useUpsellSuggestion(customerId: number | string | null) {
  return useSWR(customerId ? `/ai/client/${customerId}/upsell-suggestion` : null);
}

export function useDevisAnalysis(devisId: number | string | null) {
  return useSWR(devisId ? `/ai/devis/${devisId}/analysis` : null);
}

export function useProductRecommendation(customerId: number | string | null) {
  return useSWR(customerId ? `/ai/client/${customerId}/product-recommendation` : null);
}
