"use client";

import { useState } from "react";
import Link from "next/link";
import { format } from "date-fns";
import { useEncounters } from "@/hooks/use-encounters";
import { StatusBadge } from "@/components/shared/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { PlusCircle, FileText, Mic, Camera, Keyboard } from "lucide-react";
import type { InputMethod } from "@/types";

const inputMethodIcons: Record<InputMethod, typeof FileText> = {
  paste: Keyboard,
  recording: Mic,
  dictation: FileText,
  scan: Camera,
};

export function EncountersList() {
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const params: Record<string, string> = {};
  if (statusFilter !== "all") params.status = statusFilter;

  const { data, isLoading, error } = useEncounters(params);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Encounters</h1>
        <Link href="/encounters/new">
          <Button>
            <PlusCircle className="mr-2 h-4 w-4" />
            New Encounter
          </Button>
        </Link>
      </div>

      <div className="flex gap-4">
        <Select value={statusFilter} onValueChange={(v) => { if (v != null) setStatusFilter(String(v)); }}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Filter by status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Statuses</SelectItem>
            <SelectItem value="uploading">Uploading</SelectItem>
            <SelectItem value="transcribing">Transcribing</SelectItem>
            <SelectItem value="generating_note">Generating Note</SelectItem>
            <SelectItem value="generating_summary">Generating Summary</SelectItem>
            <SelectItem value="ready_for_review">Ready for Review</SelectItem>
            <SelectItem value="approved">Approved</SelectItem>
            <SelectItem value="delivered">Delivered</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {isLoading && (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-20 w-full" />
          ))}
        </div>
      )}

      {error && (
        <Card>
          <CardContent className="py-8 text-center text-destructive">
            Failed to load encounters. Please try again.
          </CardContent>
        </Card>
      )}

      {data && data.results.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground">No encounters found.</p>
            <Link href="/encounters/new">
              <Button variant="outline" className="mt-4">
                <PlusCircle className="mr-2 h-4 w-4" />
                Create your first encounter
              </Button>
            </Link>
          </CardContent>
        </Card>
      )}

      {data && data.results.length > 0 && (
        <div className="space-y-2">
          {data.results.map((encounter) => {
            const Icon = inputMethodIcons[encounter.input_method];
            return (
              <Link key={encounter.id} href={`/encounters/${encounter.id}`}>
                <Card className="hover:bg-muted/50 transition-colors cursor-pointer">
                  <CardContent className="flex items-center justify-between py-4">
                    <div className="flex items-center gap-4">
                      <Icon className="h-5 w-5 text-muted-foreground" />
                      <div>
                        <p className="font-medium">
                          {format(new Date(encounter.encounter_date), "MMM d, yyyy")}
                        </p>
                        <p className="text-sm text-muted-foreground capitalize">
                          {encounter.input_method}
                        </p>
                      </div>
                    </div>
                    <StatusBadge status={encounter.status} />
                  </CardContent>
                </Card>
              </Link>
            );
          })}
        </div>
      )}

      {data && data.count > 20 && (
        <div className="flex justify-center">
          <p className="text-sm text-muted-foreground">
            Showing {data.results.length} of {data.count} encounters
          </p>
        </div>
      )}
    </div>
  );
}
