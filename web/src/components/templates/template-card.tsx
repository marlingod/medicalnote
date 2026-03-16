"use client";

import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { RatingStars } from "@/components/templates/rating-stars";
import { SPECIALTY_LABELS, TEMPLATE_STATUS_LABELS } from "@/lib/constants";
import { Heart, Copy, Users, Eye } from "lucide-react";
import { cn } from "@/lib/utils";
import type { NoteTemplateListItem } from "@/types";

interface TemplateCardProps {
  template: NoteTemplateListItem;
  onClone?: (id: string) => void;
  onToggleFavorite?: (id: string, favorited: boolean) => void;
  showActions?: boolean;
}

const visibilityIcons: Record<string, typeof Eye> = {
  private: Eye,
  practice: Users,
  public: Eye,
};

export function TemplateCard({
  template,
  onClone,
  onToggleFavorite,
  showActions = true,
}: TemplateCardProps) {
  const VisibilityIcon = visibilityIcons[template.visibility] || Eye;

  return (
    <Link href={`/templates/${template.id}`}>
      <Card className="hover:bg-muted/50 transition-colors cursor-pointer h-full">
        <CardHeader className="pb-2">
          <div className="flex items-start justify-between gap-2">
            <CardTitle className="text-base line-clamp-1">
              {template.name}
            </CardTitle>
            <div className="flex items-center gap-1 shrink-0">
              <Badge variant="outline" className="text-xs">
                {SPECIALTY_LABELS[template.specialty] || template.specialty}
              </Badge>
              {template.status !== "published" && (
                <Badge variant="secondary" className="text-xs">
                  {TEMPLATE_STATUS_LABELS[template.status] || template.status}
                </Badge>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {template.description && (
            <p className="text-sm text-muted-foreground line-clamp-2">
              {template.description}
            </p>
          )}

          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            <RatingStars
              rating={template.average_rating}
              count={template.rating_count}
              size="sm"
            />
            <span className="flex items-center gap-1">
              <Copy className="h-3 w-3" />
              {template.use_count} uses
            </span>
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <VisibilityIcon className="h-3 w-3" />
              <span>{template.author_name}</span>
            </div>

            {template.tags.length > 0 && (
              <div className="flex gap-1">
                {template.tags.slice(0, 2).map((tag) => (
                  <Badge key={tag} variant="secondary" className="text-xs px-1.5 py-0">
                    {tag}
                  </Badge>
                ))}
                {template.tags.length > 2 && (
                  <span className="text-xs text-muted-foreground">
                    +{template.tags.length - 2}
                  </span>
                )}
              </div>
            )}
          </div>

          {showActions && (
            <div className="flex items-center gap-2 pt-1">
              {onToggleFavorite && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 px-2"
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    onToggleFavorite(template.id, template.is_favorited);
                  }}
                >
                  <Heart
                    className={cn(
                      "h-3.5 w-3.5",
                      template.is_favorited && "fill-red-500 text-red-500"
                    )}
                  />
                </Button>
              )}
              {onClone && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 px-2"
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    onClone(template.id);
                  }}
                >
                  <Copy className="h-3.5 w-3.5 mr-1" />
                  Clone
                </Button>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </Link>
  );
}
