"use client";

import { usePractice, usePracticeStats, useUpdatePractice } from "@/hooks/use-practice";
import { useAuth } from "@/lib/auth-context";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { useState } from "react";

export function SettingsPage() {
  const { user } = useAuth();
  const { data: practice, isLoading: practiceLoading } = usePractice();
  const { data: stats, isLoading: statsLoading } = usePracticeStats();
  const updatePractice = useUpdatePractice();

  const [practiceName, setPracticeName] = useState("");
  const [practicePhone, setPracticePhone] = useState("");

  const handleSave = async () => {
    const data: Record<string, string> = {};
    if (practiceName) data.name = practiceName;
    if (practicePhone) data.phone = practicePhone;
    if (Object.keys(data).length > 0) {
      await updatePractice.mutateAsync(data);
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
