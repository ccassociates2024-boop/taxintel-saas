"use client";

import { useEffect, useState } from "react";

interface TenantData {
  id: string;
  legal_name: string;
  trade_name: string;
  gstin: string | null;
  billing_email: string;
  place_of_supply_state_code: string;
  plan: string;
  is_active: boolean;
}

const STATE_CODES = [
  ["01", "Jammu & Kashmir"],
  ["02", "Himachal Pradesh"],
  ["03", "Punjab"],
  ["04", "Chandigarh"],
  ["05", "Uttarakhand"],
  ["06", "Haryana"],
  ["07", "Delhi"],
  ["08", "Rajasthan"],
  ["09", "Uttar Pradesh"],
  ["10", "Bihar"],
  ["11", "Sikkim"],
  ["12", "Arunachal Pradesh"],
  ["13", "Nagaland"],
  ["14", "Manipur"],
  ["15", "Mizoram"],
  ["16", "Tripura"],
  ["17", "Meghalaya"],
  ["18", "Assam"],
  ["19", "West Bengal"],
  ["20", "Jharkhand"],
  ["21", "Odisha"],
  ["22", "Chhattisgarh"],
  ["23", "Madhya Pradesh"],
  ["24", "Gujarat"],
  ["27", "Maharashtra"],
  ["29", "Karnataka"],
  ["32", "Kerala"],
  ["33", "Tamil Nadu"],
  ["36", "Telangana"],
  ["37", "Andhra Pradesh"],
];

export default function FirmSettingsPage() {
  const [tenant, setTenant] = useState<TenantData | null>(null);
  const [form, setForm] = useState<Partial<TenantData>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  function authHeaders(): Record<string, string> {
    const token = typeof window !== "undefined" ? localStorage.getItem("taxintel_token") : null;
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  useEffect(() => {
    setLoading(true);
    fetch(`${apiBase}/api/v1/tenant`, { headers: authHeaders() })
      .then(async (r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json() as Promise<TenantData>;
      })
      .then((data) => {
        setTenant(data);
        setForm(data);
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSuccess(false);

    const patch = {
      legal_name: form.legal_name,
      trade_name: form.trade_name,
      gstin: form.gstin || null,
      billing_email: form.billing_email,
      place_of_supply_state_code: form.place_of_supply_state_code,
    };

    try {
      const r = await fetch(`${apiBase}/api/v1/tenant`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify(patch),
      });
      if (!r.ok) {
        const body = await r.json().catch(() => ({}));
        throw new Error((body as { detail?: string }).detail ?? `HTTP ${r.status}`);
      }
      const updated = (await r.json()) as TenantData;
      setTenant(updated);
      setForm(updated);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setSaving(false);
    }
  }

  function field(
    label: string,
    key: keyof TenantData,
    opts: { required?: boolean; placeholder?: string } = {},
  ) {
    return (
      <div className="flex flex-col gap-1">
        <label className="text-sm font-medium text-gray-700">
          {label}
          {opts.required && <span className="text-red-500 ml-0.5">*</span>}
        </label>
        <input
          type="text"
          required={opts.required}
          placeholder={opts.placeholder}
          value={(form[key] as string) ?? ""}
          onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
          className="rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-gray-500 text-sm animate-pulse">Loading firm details…</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-10 px-4">
      <div className="mx-auto max-w-2xl">
        <header className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900">Firm Settings</h1>
          <p className="text-sm text-gray-500 mt-1">
            Update your CA firm&apos;s legal and billing details.
          </p>
          {tenant && (
            <span className="inline-block mt-2 rounded-full bg-indigo-50 px-3 py-0.5 text-xs font-medium text-indigo-700 uppercase tracking-wide">
              {tenant.plan} plan
            </span>
          )}
        </header>

        {error && (
          <div className="mb-4 rounded-md bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}
        {success && (
          <div className="mb-4 rounded-md bg-green-50 border border-green-200 px-4 py-3 text-sm text-green-700">
            Firm details saved successfully.
          </div>
        )}

        <form
          onSubmit={handleSubmit}
          className="bg-white rounded-xl shadow-sm border border-gray-200 divide-y divide-gray-100"
        >
          <section className="px-6 py-6 flex flex-col gap-5">
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">
              Legal Identity
            </h2>
            {field("Legal Name", "legal_name", { required: true, placeholder: "As per CA registration" })}
            {field("Trade / Display Name", "trade_name", { required: true, placeholder: "Name shown to clients" })}
            {field("GSTIN", "gstin", { placeholder: "22AAAAA0000A1Z5 (optional)" })}
          </section>

          <section className="px-6 py-6 flex flex-col gap-5">
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">
              Billing &amp; Place of Supply
            </h2>
            {field("Billing Email", "billing_email", { required: true, placeholder: "invoices@yourfirm.in" })}

            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium text-gray-700">
                Place of Supply (State)
                <span className="text-red-500 ml-0.5">*</span>
              </label>
              <select
                required
                value={form.place_of_supply_state_code ?? "07"}
                onChange={(e) =>
                  setForm((f) => ({ ...f, place_of_supply_state_code: e.target.value }))
                }
                className="rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white"
              >
                {STATE_CODES.map(([code, name]) => (
                  <option key={code} value={code}>
                    {code} — {name}
                  </option>
                ))}
              </select>
              <p className="text-xs text-gray-400">
                Determines CGST/SGST vs IGST on invoices raised to clients.
              </p>
            </div>
          </section>

          <div className="px-6 py-4 flex justify-end">
            <button
              type="submit"
              disabled={saving}
              className="rounded-md bg-indigo-600 px-5 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-700 disabled:opacity-50 transition-colors"
            >
              {saving ? "Saving…" : "Save Changes"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
