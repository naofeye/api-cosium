"use client";

import { useState } from "react";
import useSWR from "swr";
import { fetchJson } from "@/lib/api";
import { useToast } from "@/components/ui/Toast";
import { PageLayout } from "@/components/layout/PageLayout";
import { Button } from "@/components/ui/Button";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { Trash2, RotateCcw, Users } from "lucide-react";

interface DeletedClient {
  id: number;
  first_name: string;
  last_name: string;
  email: string | null;
  phone: string | null;
  deleted_at: string | null;
}

interface ClientListResponse {
  items: DeletedClient[];
  total: number;
}

export default function DeletedClientsPage() {
  const { toast } = useToast();
  const [restoring, setRestoring] = useState<number | null>(null);

  const { data, error, isLoading, mutate } = useSWR<ClientListResponse>(
    "/clients?include_deleted=true&page_size=100"
  );

  // Filtrer seulement les clients supprimes (deleted_at != null)
  const deletedClients = (data?.items ?? []).filter(
    (c) => c.deleted_at != null
  );

  const handleRestore = async (clientId: number) => {
    setRestoring(clientId);
    try {
      await fetchJson(`/clients/${clientId}/restore`, { method: "POST" });
      toast("Client restaure avec succes", "success");
      mutate();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Erreur lors de la restauration", "error");
    } finally {
      setRestoring(null);
    }
  };

  return (
    <PageLayout
      title="Clients supprimes"
      description="Restaurer les clients supprimes par erreur"
      breadcrumb={[{ label: "Admin", href: "/admin" }, { label: "Clients supprimes" }]}
    >
      {isLoading ? (
        <LoadingState text="Chargement des clients supprimes..." />
      ) : error ? (
        <ErrorState message="Impossible de charger les clients supprimes" onRetry={() => mutate()} />
      ) : deletedClients.length === 0 ? (
        <EmptyState
          icon={Users}
          title="Aucun client supprime"
          description="Tous les clients sont actifs. Aucun client n'a ete supprime."
        />
      ) : (
        <div className="rounded-xl border border-border bg-bg-card shadow-sm">
          <div className="px-4 py-3 border-b border-border">
            <p className="text-sm text-text-secondary">
              {deletedClients.length} client(s) supprime(s)
            </p>
          </div>
          <div className="divide-y divide-border">
            {deletedClients.map((client) => (
              <div key={client.id} className="flex items-center justify-between px-4 py-3">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="h-8 w-8 rounded-full bg-red-100 flex items-center justify-center">
                    <Trash2 className="h-4 w-4 text-red-500" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-text-primary truncate">
                      {client.last_name} {client.first_name}
                    </p>
                    <p className="text-xs text-text-secondary truncate">
                      {client.email || client.phone || `#${client.id}`}
                      {client.deleted_at && ` — supprime le ${new Date(client.deleted_at).toLocaleDateString("fr-FR")}`}
                    </p>
                  </div>
                </div>
                <Button
                  variant="outline"
                  onClick={() => handleRestore(client.id)}
                  disabled={restoring === client.id}
                >
                  <RotateCcw className={`h-4 w-4 mr-1 ${restoring === client.id ? "animate-spin" : ""}`} />
                  {restoring === client.id ? "Restauration..." : "Restaurer"}
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}
    </PageLayout>
  );
}
