"use client";

import { useEffect, useState } from "react";
import { Sparkles } from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api, Client } from "@/lib/api";

type Recommendation = { title: string; category: string; priority: string; estimated_savings: string; summary: string };

export default function RecommendationsPage() {
  const [clients, setClients] = useState<Client[]>([]);
  const [clientId, setClientId] = useState("");
  const [salary, setSalary] = useState("1200000");
  const [deductions, setDeductions] = useState("150000");
  const [items, setItems] = useState<Recommendation[]>([]);

  useEffect(() => {
    api<Client[]>("/api/v1/clients").then((data) => {
      setClients(data);
      setClientId(data[0]?.id ?? "");
    });
  }, []);

  async function generate() {
    const payload = { assessment_year: "2026-27", salary, deductions, tax_credits: "90000", capital_gains: "50000", business_income: "0", house_property_income: "0" };
    setItems(await api<Recommendation[]>(`/api/v1/recommendations/${clientId}/generate`, { method: "POST", body: JSON.stringify(payload) }));
  }

  return (
    <AppShell>
      <div className="grid gap-6 xl:grid-cols-[420px_1fr]">
        <Card>
          <CardHeader><CardTitle>Generate AI Tax Advice</CardTitle></CardHeader>
          <CardContent className="grid gap-3">
            <select value={clientId} onChange={(e) => setClientId(e.target.value)} className="h-10 rounded-md border bg-card px-3 text-sm">
              {clients.map((client) => <option key={client.id} value={client.id}>{client.full_name}</option>)}
            </select>
            <Input value={salary} onChange={(e) => setSalary(e.target.value)} placeholder="Salary" />
            <Input value={deductions} onChange={(e) => setDeductions(e.target.value)} placeholder="Deductions claimed" />
            <Button onClick={generate}><Sparkles size={18} className="mr-2" />Generate recommendations</Button>
          </CardContent>
        </Card>
        <div className="grid gap-4">
          {items.map((item) => (
            <Card key={item.title}>
              <CardContent className="pt-5">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <span className="text-xs font-bold uppercase text-primary">{item.category}</span>
                    <h2 className="mt-1 text-lg font-bold">{item.title}</h2>
                    <p className="mt-2 text-sm text-muted">{item.summary}</p>
                  </div>
                  <span className="rounded-full bg-primary/10 px-3 py-1 text-xs font-bold text-primary">{item.priority}</span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </AppShell>
  );
}

