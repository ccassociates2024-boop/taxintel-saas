"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useTheme } from "next-themes";
import { BarChart3, FileUp, LayoutDashboard, LogOut, Moon, Sparkles, Sun, Users } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const nav = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/clients", label: "Clients", icon: Users },
  { href: "/uploads", label: "Uploads", icon: FileUp },
  { href: "/recommendations", label: "Recommendations", icon: Sparkles },
  { href: "/reports", label: "Reports", icon: BarChart3 }
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { theme, setTheme } = useTheme();

  function logout() {
    localStorage.removeItem("taxintel_token");
    localStorage.removeItem("taxintel_user");
    router.push("/login");
  }

  return (
    <div className="min-h-screen bg-background">
      <aside className="fixed inset-y-0 left-0 hidden w-72 border-r bg-card p-5 lg:block">
        <div className="mb-8 flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-lg bg-primary text-white">
            <Sparkles size={20} />
          </div>
          <div>
            <strong>TaxIntel AI</strong>
            <p className="text-xs text-muted">CA SaaS Workspace</p>
          </div>
        </div>
        <nav className="grid gap-1">
          {nav.map((item) => {
            const Icon = item.icon;
            return (
              <Link key={item.href} href={item.href} className={cn("flex h-10 items-center gap-3 rounded-md px-3 text-sm font-semibold text-muted hover:bg-muted/10", pathname === item.href && "bg-primary/10 text-primary")}>
                <Icon size={18} />
                {item.label}
              </Link>
            );
          })}
        </nav>
      </aside>
      <div className="lg:pl-72">
        <header className="sticky top-0 z-10 flex h-16 items-center justify-between border-b bg-background/90 px-4 backdrop-blur lg:px-8">
          <div>
            <p className="text-xs font-bold uppercase text-muted">Indian Tax Intelligence</p>
            <h1 className="font-bold">AI-powered tax advisory platform</h1>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" className="w-10 px-0" onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>
              {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
            </Button>
            <Button variant="ghost" onClick={logout}>
              <LogOut size={18} className="mr-2" />
              Logout
            </Button>
          </div>
        </header>
        <main className="p-4 lg:p-8">{children}</main>
      </div>
    </div>
  );
}

