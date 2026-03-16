"use client";

import { useQualityScore, useTriggerQualityScore } from "@/hooks/use-quality";
import { QualityScoreBadge } from "@/components/quality/quality-score-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import {
  CheckCircle,
  XCircle,
  AlertCircle,
  RefreshCw,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface QualityScoreDetailProps {
  encounterId: string;
  enabled?: boolean;
}

const statusIcons = {
  present: CheckCircle,
  missing: XCircle,
  partial: AlertCircle,
};

const statusColors = {
  present: "text-green-600",
  missing: "text-red-500",
  partial: "text-yellow-600",
};

export function QualityScoreDetail({
  encounterId,
  enabled = true,
}: QualityScoreDetailProps) {
  const {
    data: qualityScore,
    isLoading,
    error,
  } = useQualityScore(encounterId, enabled);
  const triggerScore = useTriggerQualityScore();

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-32" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-20 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (error || !qualityScore) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center justify-between">
            Quality Score
            <Button
              variant="outline"
              size="sm"
              onClick={() => triggerScore.mutate(encounterId)}
              disabled={triggerScore.isPending}
            >
              {triggerScore.isPending ? (
                <Loader2 className="h-4 w-4 mr-1 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4 mr-1" />
              )}
              Score Note
            </Button>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No quality score available yet. Click &quot;Score Note&quot; to
            generate one.
          </p>
        </CardContent>
      </Card>
    );
  }

  const categoryEntries = Object.entries(qualityScore.category_scores);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Quality Score</CardTitle>
          <div className="flex items-center gap-2">
            <QualityScoreBadge
              score={qualityScore.overall_score}
              level={qualityScore.score_level}
            />
            <Button
              variant="ghost"
              size="sm"
              className="h-7 w-7 p-0"
              onClick={() => triggerScore.mutate(encounterId)}
              disabled={triggerScore.isPending}
            >
              {triggerScore.isPending ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <RefreshCw className="h-3.5 w-3.5" />
              )}
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Category Scores */}
        {categoryEntries.length > 0 && (
          <div className="space-y-3">
            <h4 className="text-sm font-medium">Category Breakdown</h4>
            <div className="grid grid-cols-2 gap-3">
              {categoryEntries.map(([category, data]) => (
                <div key={category} className="rounded-md border p-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium capitalize">
                      {category.replace(/_/g, " ")}
                    </span>
                    <span className="text-sm font-semibold">
                      {data.score}/{data.max_score}
                    </span>
                  </div>
                  <div className="w-full bg-muted rounded-full h-2">
                    <div
                      className={cn(
                        "h-2 rounded-full transition-all",
                        data.score / data.max_score >= 0.9
                          ? "bg-green-500"
                          : data.score / data.max_score >= 0.75
                            ? "bg-blue-500"
                            : data.score / data.max_score >= 0.5
                              ? "bg-yellow-500"
                              : "bg-red-500"
                      )}
                      style={{
                        width: `${(data.score / data.max_score) * 100}%`,
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* E/M Level */}
        {(qualityScore.em_level_suggested || qualityScore.em_level_documented) && (
          <div className="flex items-center gap-4">
            {qualityScore.em_level_suggested && (
              <div className="text-sm">
                <span className="text-muted-foreground">Suggested E/M: </span>
                <Badge variant="outline">{qualityScore.em_level_suggested}</Badge>
              </div>
            )}
            {qualityScore.em_level_documented && (
              <div className="text-sm">
                <span className="text-muted-foreground">Documented E/M: </span>
                <Badge variant="outline">
                  {qualityScore.em_level_documented}
                </Badge>
              </div>
            )}
          </div>
        )}

        {/* Findings */}
        {qualityScore.findings.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-sm font-medium">Findings</h4>
            <div className="space-y-1.5 max-h-48 overflow-y-auto">
              {qualityScore.findings.map((finding, idx) => {
                const Icon = statusIcons[finding.status] || AlertCircle;
                const color = statusColors[finding.status] || "text-muted-foreground";
                return (
                  <div
                    key={idx}
                    className="flex items-start gap-2 text-sm"
                  >
                    <Icon className={cn("h-4 w-4 mt-0.5 shrink-0", color)} />
                    <div>
                      <span className="font-medium capitalize">
                        {finding.element}
                      </span>
                      {finding.detail && (
                        <span className="text-muted-foreground">
                          {" "}
                          - {finding.detail}
                        </span>
                      )}
                      {finding.suggestion && (
                        <p className="text-xs text-muted-foreground mt-0.5">
                          Suggestion: {finding.suggestion}
                        </p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Suggestions */}
        {qualityScore.suggestions.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-sm font-medium">Improvement Suggestions</h4>
            <ul className="space-y-1">
              {qualityScore.suggestions.map((suggestion, idx) => (
                <li
                  key={idx}
                  className="text-sm text-muted-foreground flex items-start gap-2"
                >
                  <span className="text-primary mt-1 shrink-0">
                    &#8226;
                  </span>
                  {suggestion}
                </li>
              ))}
            </ul>
          </div>
        )}

        <p className="text-xs text-muted-foreground">
          Rules v{qualityScore.rules_version} &middot; Last scored{" "}
          {new Date(qualityScore.scored_at).toLocaleString()}
        </p>
      </CardContent>
    </Card>
  );
}
