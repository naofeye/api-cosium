"use client";

import { PolarAngleAxis, PolarGrid, Radar, RadarChart, ResponsiveContainer } from "recharts";

interface ClientScoreRadarProps {
  /**
   * Score client ventile sur 5 axes (0-100 chacun).
   * Si un score manque, il sera affiche a 0.
   */
  scores: {
    frequence?: number;
    panier?: number;
    anciennete?: number;
    pec?: number;
    renouvellement?: number;
  };
  height?: number;
}

/**
 * Radar 5 axes pour visualiser le score client.
 */
export function ClientScoreRadar({ scores, height = 240 }: ClientScoreRadarProps) {
  const data = [
    { axis: "Frequence", value: scores.frequence ?? 0 },
    { axis: "Panier", value: scores.panier ?? 0 },
    { axis: "Anciennete", value: scores.anciennete ?? 0 },
    { axis: "PEC", value: scores.pec ?? 0 },
    { axis: "Renouv.", value: scores.renouvellement ?? 0 },
  ];
  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart cx="50%" cy="50%" outerRadius="70%" data={data}>
          <PolarGrid stroke="#e5e7eb" />
          <PolarAngleAxis dataKey="axis" tick={{ fontSize: 12, fill: "#6b7280" }} />
          <Radar
            name="Score"
            dataKey="value"
            stroke="#2563eb"
            fill="#2563eb"
            fillOpacity={0.25}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
