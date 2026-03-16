"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useSendSummary } from "@/hooks/use-summaries";
import type { PatientSummary, DeliveryMethod } from "@/types";
import { Send, Languages } from "lucide-react";

interface SummaryPreviewProps {
  summary: PatientSummary;
  encounterId: string;
  onSent?: () => void;
}

export function SummaryPreview({
  summary,
  encounterId,
  onSent,
}: SummaryPreviewProps) {
  const [deliveryMethod, setDeliveryMethod] = useState<DeliveryMethod>("app");
  const sendSummary = useSendSummary();

  const handleSend = async () => {
    await sendSummary.mutateAsync({
      encounterId,
      data: { delivery_method: deliveryMethod },
    });
    onSent?.();
  };

  const isSent = summary.delivery_status !== "pending";

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div className="space-y-1">
          <CardTitle className="text-lg">Patient Summary</CardTitle>
          <div className="flex gap-2">
            <Badge variant="outline" className="capitalize">
              {summary.reading_level.replace("_", " ")}
            </Badge>
            <Badge
              variant={isSent ? "default" : "secondary"}
              className={isSent ? "bg-green-100 text-green-800" : ""}
            >
              {summary.delivery_status}
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <Tabs defaultValue="en">
          <TabsList>
            <TabsTrigger value="en">
              <Languages className="mr-2 h-4 w-4" />
              English
            </TabsTrigger>
            {summary.summary_es && (
              <TabsTrigger value="es">
                <Languages className="mr-2 h-4 w-4" />
                Spanish
              </TabsTrigger>
            )}
          </TabsList>
          <TabsContent value="en" className="mt-4">
            <div className="prose prose-sm max-w-none">
              <p className="whitespace-pre-wrap">{summary.summary_en}</p>
            </div>
          </TabsContent>
          {summary.summary_es && (
            <TabsContent value="es" className="mt-4">
              <div className="prose prose-sm max-w-none">
                <p className="whitespace-pre-wrap">{summary.summary_es}</p>
              </div>
            </TabsContent>
          )}
        </Tabs>

        {summary.medical_terms_explained.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold mb-2">Medical Terms Explained</h4>
            <div className="space-y-2">
              {summary.medical_terms_explained.map((term, idx) => (
                <div key={idx} className="text-sm">
                  <span className="font-medium">{term.term}:</span>{" "}
                  <span className="text-muted-foreground">{term.explanation}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="text-xs text-muted-foreground italic border-t pt-3">
          {summary.disclaimer_text}
        </div>

        {!isSent && (
          <div className="flex gap-3 pt-4 border-t">
            <Select
              value={deliveryMethod}
              onValueChange={(v) => { if (v != null) setDeliveryMethod(String(v) as DeliveryMethod); }}
            >
              <SelectTrigger className="w-48">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="app">Mobile App</SelectItem>
                <SelectItem value="sms_link">SMS Link</SelectItem>
                <SelectItem value="email_link">Email Link</SelectItem>
                <SelectItem value="widget">Clinic Widget</SelectItem>
              </SelectContent>
            </Select>
            <Button
              onClick={handleSend}
              disabled={sendSummary.isPending}
              className="flex-1"
            >
              <Send className="mr-2 h-4 w-4" />
              {sendSummary.isPending ? "Sending..." : "Send to Patient"}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
