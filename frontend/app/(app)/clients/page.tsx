"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api, Client } from "@/lib/api";

export default function ClientsPage() {
  const [clients, setClients] = useState<Client[]>([]);
  const [form, setForm] = useState({ full_name: "Aarav Mehta", pan: "BFXPM4821K", email: "aarav@example.com", phone: "9999999999" });

  async function load() {
    setClients(await api<Client[]>("/api/v1/clients"));
  }

  useEffect(() => { load(); }, []);

  async function create(event: React.FormEvent) {
    event.preventDefault();
    await api<Client>("/api/v1/clients", { method: "POST", body: JSON.stringify({ ...form, residential_status: "RESIDENT", client_type: "INDIVIDUAL" }) });
    await load();
  }

  return (
    <AppShell>
      <div className="grid gap-6 xl:grid-cols-[420px_1fr]">
        <Card>
          <CardHeader><CardTitle>Add Client</CardTitle></CardHeader>
          <CardContent>
            <form onSubmit={create} className="grid gap-3">
              <Input value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} placeholder="Client name" />
              <Input value={form.pan} onChange={(e) => setForm({ ...form, pan: e.target.value.toUpperCase() })} placeholder="PAN" maxLength={10} />
              <Input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="Email" />
              <Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} placeholder="Phone" />
              <Button type="submit">Create client</Button>
            </form>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Client Portfolio</CardTitle></CardHeader>
          <CardContent className="grid gap-3">
            {clients.map((client) => (
              <div key={client.id} className="grid gap-2 rounded-md border p-4 md:grid-cols-[1fr_140px_140px]">
                <div><strong>{client.full_name}</strong><p className="text-sm text-muted">{client.email}</p></div>
                <span className="font-mono text-sm">{client.pan}</span>
                <span className="text-sm font-semibold text-primary">{client.client_type}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}

