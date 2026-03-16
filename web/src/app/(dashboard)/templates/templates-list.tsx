"use client";

import { useState } from "react";
import Link from "next/link";
import {
  useTemplates,
  useCloneTemplate,
  useToggleFavorite,
  useSpecialties,
} from "@/hooks/use-templates";
import { TemplateCard } from "@/components/templates/template-card";
import { SpecialtyFilter } from "@/components/templates/specialty-filter";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { PlusCircle, Search } from "lucide-react";
import type { MedicalSpecialty } from "@/types";

export function TemplatesList() {
  const [scope, setScope] = useState<"mine" | "marketplace">("mine");
  const [specialty, setSpecialty] = useState<MedicalSpecialty | "all">("all");
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState("updated_at");

  const params: Record<string, string> = { scope };
  if (specialty !== "all") params.specialty = specialty;
  if (search) params.search = search;
  if (sort) params.ordering = sort === "updated_at" ? "-updated_at" : `-${sort}`;

  const { data, isLoading, error } = useTemplates(params);
  const { data: specialties } = useSpecialties();
  const cloneTemplate = useCloneTemplate();
  const toggleFavorite = useToggleFavorite();

  const handleClone = (id: string) => {
    cloneTemplate.mutate({ id });
  };

  const handleToggleFavorite = (id: string, favorited: boolean) => {
    toggleFavorite.mutate({ id, favorited });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Templates</h1>
        <Link href="/templates/new">
          <Button>
            <PlusCircle className="mr-2 h-4 w-4" />
            New Template
          </Button>
        </Link>
      </div>

      <Tabs
        value={scope}
        onValueChange={(v) => setScope(v as "mine" | "marketplace")}
      >
        <TabsList>
          <TabsTrigger value="mine">My Templates</TabsTrigger>
          <TabsTrigger value="marketplace">Marketplace</TabsTrigger>
        </TabsList>

        <div className="mt-4 space-y-4">
          {/* Filters */}
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search templates..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
            <Select
              value={sort}
              onValueChange={(v) => {
                if (v != null) setSort(String(v));
              }}
            >
              <SelectTrigger className="w-44">
                <SelectValue placeholder="Sort by" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="updated_at">Recently Updated</SelectItem>
                <SelectItem value="created_at">Newest</SelectItem>
                <SelectItem value="use_count">Most Used</SelectItem>
                <SelectItem value="clone_count">Most Cloned</SelectItem>
                <SelectItem value="name">Name</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Specialty Filter */}
          <SpecialtyFilter
            selected={specialty}
            onSelect={setSpecialty}
            specialties={specialties}
          />

          {/* Content for both tabs */}
          <TabsContent value="mine" className="mt-0">
            <TemplateGrid
              data={data}
              isLoading={isLoading}
              error={error}
              onClone={handleClone}
              onToggleFavorite={handleToggleFavorite}
              emptyMessage="You have no templates yet."
              emptyAction={
                <Link href="/templates/new">
                  <Button variant="outline" className="mt-4">
                    <PlusCircle className="mr-2 h-4 w-4" />
                    Create your first template
                  </Button>
                </Link>
              }
            />
          </TabsContent>

          <TabsContent value="marketplace" className="mt-0">
            <TemplateGrid
              data={data}
              isLoading={isLoading}
              error={error}
              onClone={handleClone}
              onToggleFavorite={handleToggleFavorite}
              emptyMessage="No marketplace templates found."
            />
          </TabsContent>
        </div>
      </Tabs>
    </div>
  );
}

function TemplateGrid({
  data,
  isLoading,
  error,
  onClone,
  onToggleFavorite,
  emptyMessage,
  emptyAction,
}: {
  data: ReturnType<typeof useTemplates>["data"];
  isLoading: boolean;
  error: unknown;
  onClone: (id: string) => void;
  onToggleFavorite: (id: string, favorited: boolean) => void;
  emptyMessage: string;
  emptyAction?: React.ReactNode;
}) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <Skeleton key={i} className="h-48 w-full" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-destructive">
          Failed to load templates. Please try again.
        </CardContent>
      </Card>
    );
  }

  if (data && data.results.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <p className="text-muted-foreground">{emptyMessage}</p>
          {emptyAction}
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {data?.results.map((template) => (
          <TemplateCard
            key={template.id}
            template={template}
            onClone={onClone}
            onToggleFavorite={onToggleFavorite}
          />
        ))}
      </div>
      {data && data.count > 20 && (
        <div className="flex justify-center mt-4">
          <p className="text-sm text-muted-foreground">
            Showing {data.results.length} of {data.count} templates
          </p>
        </div>
      )}
    </>
  );
}
