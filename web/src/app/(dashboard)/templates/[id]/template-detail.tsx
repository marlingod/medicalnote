"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  useTemplate,
  useCloneTemplate,
  useToggleFavorite,
  useRateTemplate,
  useDeleteTemplate,
} from "@/hooks/use-templates";
import { useAuth } from "@/lib/auth-context";
import { RatingStars } from "@/components/templates/rating-stars";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  SPECIALTY_LABELS,
  TEMPLATE_STATUS_LABELS,
  TEMPLATE_VISIBILITY_LABELS,
} from "@/lib/constants";
import {
  ArrowLeft,
  Copy,
  Heart,
  Pencil,
  Trash2,
  Star,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { TemplateRating } from "@/types";

interface TemplateDetailProps {
  templateId: string;
}

export function TemplateDetail({ templateId }: TemplateDetailProps) {
  const router = useRouter();
  const { user } = useAuth();
  const { data: template, isLoading } = useTemplate(templateId);
  const cloneTemplate = useCloneTemplate();
  const toggleFavorite = useToggleFavorite();
  const rateTemplate = useRateTemplate();
  const deleteTemplate = useDeleteTemplate();

  const [showRateForm, setShowRateForm] = useState(false);
  const [rateScore, setRateScore] = useState(0);
  const [rateReview, setRateReview] = useState("");

  const isOwner = template && user && template.author_name?.includes(user.last_name);

  const handleClone = async () => {
    if (!template) return;
    try {
      const cloned = await cloneTemplate.mutateAsync({ id: template.id });
      router.push(`/templates/${cloned.id}`);
    } catch {
      // Error handled by mutation
    }
  };

  const handleToggleFavorite = () => {
    if (!template) return;
    toggleFavorite.mutate({
      id: template.id,
      favorited: template.is_favorited,
    });
  };

  const handleRate = async () => {
    if (!template || rateScore === 0) return;
    try {
      await rateTemplate.mutateAsync({
        id: template.id,
        data: { score: rateScore, review: rateReview },
      });
      setShowRateForm(false);
      setRateScore(0);
      setRateReview("");
    } catch {
      // Error handled by mutation
    }
  };

  const handleDelete = async () => {
    if (!template) return;
    if (!confirm("Are you sure you want to delete this template?")) return;
    try {
      await deleteTemplate.mutateAsync(template.id);
      router.push("/templates");
    } catch {
      // Error handled by mutation
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (!template) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <p className="text-muted-foreground">Template not found.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link href="/templates">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-5 w-5" />
          </Button>
        </Link>
        <div className="flex-1">
          <h1 className="text-2xl font-bold">{template.name}</h1>
          <p className="text-sm text-muted-foreground">
            by {template.author_name} &middot; v{template.version}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline">
            {SPECIALTY_LABELS[template.specialty] || template.specialty}
          </Badge>
          <Badge variant="secondary">
            {TEMPLATE_STATUS_LABELS[template.status] || template.status}
          </Badge>
          <Badge variant="outline">
            {TEMPLATE_VISIBILITY_LABELS[template.visibility] || template.visibility}
          </Badge>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={handleToggleFavorite}
          disabled={toggleFavorite.isPending}
        >
          <Heart
            className={cn(
              "h-4 w-4 mr-1",
              template.is_favorited && "fill-red-500 text-red-500"
            )}
          />
          {template.is_favorited ? "Unfavorite" : "Favorite"}
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={handleClone}
          disabled={cloneTemplate.isPending}
        >
          {cloneTemplate.isPending ? (
            <Loader2 className="h-4 w-4 mr-1 animate-spin" />
          ) : (
            <Copy className="h-4 w-4 mr-1" />
          )}
          Clone
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setShowRateForm(!showRateForm)}
        >
          <Star className="h-4 w-4 mr-1" />
          Rate
        </Button>
        {isOwner && (
          <>
            <Link href={`/templates/edit/${template.id}`}>
              <Button variant="outline" size="sm">
                <Pencil className="h-4 w-4 mr-1" />
                Edit
              </Button>
            </Link>
            <Button
              variant="outline"
              size="sm"
              onClick={handleDelete}
              disabled={deleteTemplate.isPending}
              className="text-destructive hover:text-destructive"
            >
              <Trash2 className="h-4 w-4 mr-1" />
              Delete
            </Button>
          </>
        )}
      </div>

      {/* Rate Form */}
      {showRateForm && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Rate This Template</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Rating</Label>
              <RatingStars
                rating={rateScore}
                size="lg"
                interactive
                onRate={setRateScore}
              />
            </div>
            <div className="space-y-2">
              <Label>Review (optional)</Label>
              <Textarea
                value={rateReview}
                onChange={(e) => setRateReview(e.target.value)}
                placeholder="Share your experience with this template..."
                className="min-h-[80px]"
              />
            </div>
            <div className="flex gap-2">
              <Button
                size="sm"
                onClick={handleRate}
                disabled={rateScore === 0 || rateTemplate.isPending}
              >
                {rateTemplate.isPending ? "Submitting..." : "Submit Rating"}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowRateForm(false)}
              >
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Description */}
      {template.description && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Description</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm">{template.description}</p>
          </CardContent>
        </Card>
      )}

      {/* Stats */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Template Info</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-sm text-muted-foreground">Rating</p>
              <RatingStars
                rating={template.average_rating}
                count={template.rating_count}
                size="md"
              />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Uses</p>
              <p className="text-lg font-semibold">{template.use_count}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Clones</p>
              <p className="text-lg font-semibold">{template.clone_count}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Note Type</p>
              <p className="text-lg font-semibold uppercase">
                {template.note_type.replace(/_/g, " ")}
              </p>
            </div>
          </div>

          {template.tags.length > 0 && (
            <div className="mt-4">
              <p className="text-sm text-muted-foreground mb-2">Tags</p>
              <div className="flex flex-wrap gap-1">
                {template.tags.map((tag) => (
                  <Badge key={tag} variant="secondary">
                    {tag}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Schema Preview */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Template Schema</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {template.schema.sections.map((section) => (
            <div key={section.key} className="rounded-md border p-4">
              <h4 className="font-medium mb-2">{section.label}</h4>
              <div className="space-y-2">
                {section.fields.map((field) => (
                  <div
                    key={field.key}
                    className="flex items-center justify-between text-sm"
                  >
                    <div className="flex items-center gap-2">
                      <span>{field.label}</span>
                      {field.required && (
                        <span className="text-destructive text-xs">*</span>
                      )}
                      {field.ai_prompt && (
                        <Badge variant="secondary" className="text-xs px-1.5 py-0">
                          AI
                        </Badge>
                      )}
                    </div>
                    <Badge variant="outline" className="text-xs">
                      {field.type}
                    </Badge>
                  </div>
                ))}
              </div>
            </div>
          ))}

          {template.schema.ai_instructions && (
            <div className="rounded-md border border-primary/20 bg-primary/5 p-3">
              <p className="text-sm font-medium text-primary mb-1">
                AI Instructions
              </p>
              <p className="text-sm text-muted-foreground">
                {template.schema.ai_instructions}
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Ratings */}
      {template.ratings.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">
              Reviews ({template.ratings.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {template.ratings.map((rating: TemplateRating) => (
              <div key={rating.id} className="border-b pb-3 last:border-0">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium">{rating.user_name}</span>
                  <RatingStars rating={rating.score} size="sm" />
                </div>
                {rating.review && (
                  <p className="text-sm text-muted-foreground">{rating.review}</p>
                )}
                <p className="text-xs text-muted-foreground mt-1">
                  {new Date(rating.created_at).toLocaleDateString()}
                </p>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
