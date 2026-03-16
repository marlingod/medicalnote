"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  FileText,
  Users,
  PlusCircle,
  Settings,
  LogOut,
  Stethoscope,
} from "lucide-react";

const navItems = [
  { href: "/encounters", label: "Encounters", icon: FileText },
  { href: "/encounters/new", label: "New Encounter", icon: PlusCircle },
  { href: "/patients", label: "Patients", icon: Users },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <aside className="flex h-screen w-64 flex-col border-r bg-card">
      <div className="flex items-center gap-2 border-b px-6 py-4">
        <Stethoscope className="h-6 w-6 text-primary" />
        <span className="text-lg font-semibold">MedicalNote</span>
      </div>

      <nav className="flex-1 space-y-1 px-3 py-4">
        {navItems.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t px-3 py-4">
        <div className="mb-3 px-3">
          <p className="text-sm font-medium truncate">{user?.first_name} {user?.last_name}</p>
          <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
          {user?.practice_name && (
            <p className="text-xs text-muted-foreground truncate">{user.practice_name}</p>
          )}
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="w-full justify-start gap-3 text-muted-foreground"
          onClick={logout}
        >
          <LogOut className="h-4 w-4" />
          Sign Out
        </Button>
      </div>
    </aside>
  );
}
