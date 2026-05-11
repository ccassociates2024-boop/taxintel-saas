"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, IndianRupee, ShieldCheck, Users } from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";

type Dashboard = {
  client_count: number;
  tax_payable: string;
  refund_estimate: string;
  average_health_score: number;
  ais_mismatch_count: number;
  recent_recommendations: Array<{ title: string; priority: string; summary: string; estimated_savings: string }>;
};

export default function DashboardPage() {
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<Dashboard>("/api/v1/dashboard").then(setData).catch((err) => setError(err.message));
  }, []);

  return (
    <AppShell>
      <div className="grid gap-6">
        {error && <p className="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">{error}</p>}
        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <Metric icon={Users} label="Clients" value={data?.client_count ?? 0} />
          <Metric icon={IndianRupee} label="Tax payable" value={`₹${data?.tax_payable ?? "0"}`} />
          <Metric icon={IndianRupee} label="Refund estimate" value={`₹${data?.refund_estimate ?? "0"}`} />
          <Metric icon={AlertTriangle} label="AIS mismatches" value={data?.ais_mismatch_count ?? 0} />
        </section>
        <section className="grid gap-4 xl:grid-cols-[1fr_420px]">
          <Card>
            <CardHeader><CardTitle>Tax Health Score</CardTitle></CardHeader>
            <CardContent>
              <div className="flex items-center gap-6">
                <div className="grid h-36 w-36 place-items-center rounded-full border-8 border-primary text-4xl font-black">{data?.average_health_score ?? 0}</div>
                <div>
                  <h2 className="text-xl font-bold">Portfolio health is stable</h2>
                  <p className="mt-2 max-w-xl text-muted">Upload AIS and 26AS files, run computation, and generate AI recommendations to populate live advisory signals.</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Recent AI Recommendations</CardTitle></CardHeader>
            <CardContent className="grid gap-3">
              {(data?.recent_recommendations ?? []).map((item) => (
                <div key={item.title} className="rounded-md border p-3">
                  <div className="flex items-center justify-between gap-3">
                    <strong>{item.title}</strong>
                    <span className="rounded-full bg-primary/10 px-2 py-1 text-xs font-bold text-primary">{item.priority}</span>
                  </div>
                  <p className="mt-1 text-sm text-muted">{item.summary}</p>
                </div>
              ))}
              {!data?.recent_recommendations?.length && <p className="text-sm text-muted">No recommendations yet.</p>}
            </CardContent>
          </Card>
        </section>
      </div>
    </AppShell>
  );
}

function Metric({ icon: Icon, label, value }: { icon: React.ElementType; label: string; value: string | number }) {
  return (
    <Card>
      <CardContent className="pt-5">
        <div className="flex items-center justify-between text-muted">
          <span className="text-sm font-semibold">{label}</span>
          <Icon size={19} />
        </div>
        <strong className="mt-5 block text-3xl">{value}</strong>
      </CardContent>
    </Card>
  );
}

