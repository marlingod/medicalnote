"use client";

import { Badge } from "@/components/ui/badge";
import { QUALITY_SCORE_LEVELS, QUALITY_SCORE_COLORS } from "@/lib/constants";
import { cn } from "@/lib/utils";
import type { QualityScoreLevel } from "@/types";

interface QualityScoreBadgeProps {
  score: number;
  level: QualityScoreLevel;
  showScore?: boolean;
}

export function QualityScoreBadge({
  score,
  level,
  showScore = true,
}: QualityScoreBadgeProps) {
  const label = QUALITY_SCORE_LEVELS[level] || level;
  const colorClass = QUALITY_SCORE_COLORS[level] || "";

  return (
    <Badge variant="outline" className={cn("font-medium", colorClass)}>
      {showScore && <span className="mr-1">{Math.round(score)}%</span>}
      {label}
    </Badge>
  );
}
