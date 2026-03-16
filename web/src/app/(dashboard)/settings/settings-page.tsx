"use client";

import { usePractice, usePracticeStats, useUpdatePractice } from "@/hooks/use-practice";
import { useAuth } from "@/lib/auth-context";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { useState } from "react";
import { Brain, Zap, Scale } from "lucide-react";

const LLM_PROVIDERS = [
  {
    value: "claude",
    label: "Claude Only",
    description: "Anthropic Claude for all AI tasks. Best structured output quality.",
    icon: Brain,
    cost: "~$500/mo at 5K encounters",
    badge: "Highest Quality",
    badgeVariant: "default" as const,
  },
  {
    value: "gemini",
    label: "Gemini Only",
    description: "Google Gemini for all AI tasks. Most affordable option with strong medical accuracy.",
    icon: Zap,
    cost: "~$225/mo at 5K encounters",
    badge: "Most Affordable",
    badgeVariant: "secondary" as const,
  },
  {
    value: "claude+gemini",
    label: "Claude + Gemini",
    description: "Claude for SOAP notes & quality scoring (best reasoning). Gemini for patient summaries (cheapest).",
    icon: Scale,
    cost: "~$400/mo at 5K encounters",
    badge: "Best Value",
    badgeVariant: "outline" as const,
  },
];

export function SettingsPage() {
  const { user } = useAuth();
  const { data: practice, isLoading: practiceLoading } = usePractice();
  const { data: stats, isLoading: statsLoading } = usePracticeStats();
  const updatePractice = useUpdatePractice();

  const [practiceName, setPracticeName] = useState("");
  const [practicePhone, setPracticePhone] = useState("");
  const [llmProvider, setLlmProvider] = useState<string | null>(null);
  const [llmSaving, setLlmSaving] = useState(false);

  const currentProvider = llmProvider ?? practice?.llm_provider ?? "claude";

  const handleSave = async () => {
    const data: Record<string, string> = {};
    if (practiceName) data.name = practiceName;
    if (practicePhone) data.phone = practicePhone;
    if (Object.keys(data).length > 0) {
      await updatePractice.mutateAsync(data);
    }
  };

  const handleLlmProviderChange = async (provider: string) => {
    setLlmProvider(provider);
    setLlmSaving(true);
    try {
      await updatePractice.mutateAsync({ llm_provider: provider });
    } finally {
      setLlmSaving(false);
    }
  };

  return (
    <div className="space-y-6 max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold">Practice Settings</h1>

      <Card>
        <CardHeader>
          <CardTitle>Your Profile</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-muted-foreground">Name</p>
              <p className="font-medium">{user?.first_name} {user?.last_name}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Email</p>
              <p className="font-medium">{user?.email}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Specialty</p>
              <p className="font-medium">{user?.specialty || "Not set"}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Role</p>
              <Badge variant="outline" className="capitalize">{user?.role}</Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Practice Information</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {practiceLoading ? (
            <Skeleton className="h-20 w-full" />
          ) : practice ? (
            <>
              <div className="space-y-2">
                <Label>Practice Name</Label>
                <Input
                  defaultValue={practice.name}
                  onChange={(e) => setPracticeName(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label>Phone</Label>
                <Input
                  defaultValue={practice.phone}
                  onChange={(e) => setPracticePhone(e.target.value)}
                />
              </div>
              <div className="text-sm">
                <span className="text-muted-foreground">Subscription: </span>
                <Badge variant="outline" className="capitalize">
                  {practice.subscription_tier}
                </Badge>
              </div>
              <Button onClick={handleSave} disabled={updatePractice.isPending}>
                {updatePractice.isPending ? "Saving..." : "Save Changes"}
              </Button>
            </>
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Brain className="h-5 w-5" />
            AI Model Provider
          </CardTitle>
          <CardDescription>
            Choose which AI models power your note generation and patient summaries.
            This affects quality, speed, and cost.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {practiceLoading ? (
            <Skeleton className="h-40 w-full" />
          ) : (
            <div className="grid gap-3">
              {LLM_PROVIDERS.map((provider) => {
                const Icon = provider.icon;
                const isSelected = currentProvider === provider.value;
                return (
                  <button
                    key={provider.value}
                    onClick={() => handleLlmProviderChange(provider.value)}
                    disabled={llmSaving}
                    className={`w-full text-left rounded-lg border-2 p-4 transition-all ${
                      isSelected
                        ? "border-primary bg-primary/5"
                        : "border-border hover:border-primary/50 hover:bg-muted/50"
                    } ${llmSaving ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}`}
                  >
                    <div className="flex items-start gap-3">
                      <div className={`mt-0.5 rounded-lg p-2 ${
                        isSelected ? "bg-primary text-primary-foreground" : "bg-muted"
                      }`}>
                        <Icon className="h-4 w-4" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold">{provider.label}</span>
                          <Badge variant={provider.badgeVariant} className="text-xs">
                            {provider.badge}
                          </Badge>
                          {isSelected && (
                            <Badge className="text-xs bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
                              Active
                            </Badge>
                          )}
                        </div>
                        <p className="text-sm text-muted-foreground mt-1">
                          {provider.description}
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">
                          Estimated cost: {provider.cost}
                        </p>
                      </div>
                      <div className={`mt-1 h-4 w-4 rounded-full border-2 flex items-center justify-center ${
                        isSelected ? "border-primary" : "border-muted-foreground/30"
                      }`}>
                        {isSelected && (
                          <div className="h-2 w-2 rounded-full bg-primary" />
                        )}
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
          {llmSaving && (
            <p className="text-sm text-muted-foreground mt-3">Saving provider preference...</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Dashboard Statistics</CardTitle>
        </CardHeader>
        <CardContent>
          {statsLoading ? (
            <Skeleton className="h-20 w-full" />
          ) : stats ? (
            <div className="grid grid-cols-2 gap-6">
              <div className="text-center p-4 border rounded-lg">
                <p className="text-3xl font-bold">{stats.total_patients}</p>
                <p className="text-sm text-muted-foreground">Total Patients</p>
              </div>
              <div className="text-center p-4 border rounded-lg">
                <p className="text-3xl font-bold">{stats.total_encounters}</p>
                <p className="text-sm text-muted-foreground">Total Encounters</p>
              </div>
              {Object.entries(stats.encounters_by_status).map(([status, count]) => (
                <div key={status} className="text-center p-4 border rounded-lg">
                  <p className="text-2xl font-bold">{count}</p>
                  <p className="text-sm text-muted-foreground capitalize">
                    {status.replace(/_/g, " ")}
                  </p>
                </div>
              ))}
            </div>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
