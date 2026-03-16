"use client";

import { SPECIALTY_LABELS } from "@/lib/constants";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { MedicalSpecialty, SpecialtyInfo } from "@/types";

interface SpecialtyFilterProps {
  selected: MedicalSpecialty | "all";
  onSelect: (specialty: MedicalSpecialty | "all") => void;
  specialties?: SpecialtyInfo[];
}

const defaultSpecialties: MedicalSpecialty[] = [
  "general",
  "primary_care",
  "dermatology",
  "psychiatry",
  "cardiology",
  "orthopedics",
  "pediatrics",
  "neurology",
  "gastroenterology",
];

export function SpecialtyFilter({
  selected,
  onSelect,
  specialties,
}: SpecialtyFilterProps) {
  const items = specialties
    ? specialties.map((s) => ({ value: s.value, label: s.label, count: s.template_count }))
    : defaultSpecialties.map((s) => ({
        value: s,
        label: SPECIALTY_LABELS[s] || s,
        count: undefined as number | undefined,
      }));

  return (
    <div className="flex flex-wrap gap-2">
      <Badge
        variant={selected === "all" ? "default" : "outline"}
        className={cn(
          "cursor-pointer transition-colors",
          selected === "all" && "bg-primary text-primary-foreground"
        )}
        onClick={() => onSelect("all")}
      >
        All
      </Badge>
      {items.map((item) => (
        <Badge
          key={item.value}
          variant={selected === item.value ? "default" : "outline"}
          className={cn(
            "cursor-pointer transition-colors",
            selected === item.value && "bg-primary text-primary-foreground"
          )}
          onClick={() => onSelect(item.value)}
        >
          {item.label}
          {item.count !== undefined && (
            <span className="ml-1 opacity-70">({item.count})</span>
          )}
        </Badge>
      ))}
    </div>
  );
}
