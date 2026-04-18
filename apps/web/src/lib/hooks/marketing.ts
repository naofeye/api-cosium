import useSWR from "swr";

// --- Marketing campaigns ---
export function useCampaignRoi(campaignId: number | string | null) {
  return useSWR(campaignId ? `/marketing/campaigns/${campaignId}/roi` : null);
}

export function useCampaignAbStats(campaignId: number | string | null) {
  return useSWR(campaignId ? `/marketing/campaigns/${campaignId}/ab-stats` : null);
}
