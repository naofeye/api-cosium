"use client";

import { useState } from "react";
import useSWR from "swr";
import { PageLayout } from "@/components/layout/PageLayout";
import { Button } from "@/components/ui/Button";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { useToast } from "@/components/ui/Toast";
import { fetchJson } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { cn } from "@/lib/utils";
import {
  Plus,
  UserX,
  X,
  Eye,
  EyeOff,
  Users,
} from "lucide-react";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface AdminUser {
  id: number;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string | null;
  last_login_at: string | null;
}

interface AdminUserListResponse {
  users: AdminUser[];
  total: number;
}

const ROLE_OPTIONS = [
  { value: "admin", label: "Administrateur", color: "bg-red-50 text-red-700" },
  { value: "manager", label: "Manager", color: "bg-blue-50 text-blue-700" },
  { value: "operator", label: "Operateur", color: "bg-emerald-50 text-emerald-700" },
  { value: "viewer", label: "Lecteur", color: "bg-gray-100 text-gray-700" },
] as const;

function roleBadge(role: string) {
  const r = ROLE_OPTIONS.find((o) => o.value === role);
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        r?.color ?? "bg-gray-100 text-gray-700"
      )}
    >
      {r?.label ?? role}
    </span>
  );
}

/* ------------------------------------------------------------------ */
/*  Create User Dialog                                                 */
/* ------------------------------------------------------------------ */

function CreateUserDialog({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
}) {
  const { toast } = useToast();
  const [form, setForm] = useState({
    email: "",
    password: "",
    first_name: "",
    last_name: "",
    role: "operator",
  });
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const handleChange = (name: string, value: string) => {
    setForm((prev) => ({ ...prev, [name]: value }));
    setError("");
  };

  const isValid =
    form.email.trim().length > 0 &&
    form.password.length >= 8 &&
    /[A-Z]/.test(form.password) &&
    /\d/.test(form.password);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isValid || submitting) return;
    setSubmitting(true);
    setError("");
    try {
      await fetchJson("/admin/users", {
        method: "POST",
        body: JSON.stringify({
          email: form.email.trim(),
          password: form.password,
          first_name: form.first_name.trim(),
          last_name: form.last_name.trim(),
          role: form.role,
        }),
      });
      toast("Utilisateur cree avec succes", "success");
      setForm({ email: "", password: "", first_name: "", last_name: "", role: "operator" });
      onCreated();
      onClose();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Erreur lors de la creation";
      setError(msg);
      toast(msg, "error");
    } finally {
      setSubmitting(false);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-gray-900">
            Ajouter un utilisateur
          </h2>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
            aria-label="Fermer"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label
                htmlFor="first_name"
                className="mb-1 block text-sm font-medium text-gray-700"
              >
                Prenom
              </label>
              <input
                id="first_name"
                type="text"
                value={form.first_name}
                onChange={(e) => handleChange("first_name", e.target.value)}
                placeholder="Jean"
                className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
              />
            </div>
            <div>
              <label
                htmlFor="last_name"
                className="mb-1 block text-sm font-medium text-gray-700"
              >
                Nom
              </label>
              <input
                id="last_name"
                type="text"
                value={form.last_name}
                onChange={(e) => handleChange("last_name", e.target.value)}
                placeholder="Dupont"
                className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
              />
            </div>
          </div>

          <div>
            <label
              htmlFor="email"
              className="mb-1 block text-sm font-medium text-gray-700"
            >
              Adresse email *
            </label>
            <input
              id="email"
              type="email"
              value={form.email}
              onChange={(e) => handleChange("email", e.target.value)}
              placeholder="jean.dupont@optique.fr"
              required
              className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            />
          </div>

          <div>
            <label
              htmlFor="password"
              className="mb-1 block text-sm font-medium text-gray-700"
            >
              Mot de passe *
            </label>
            <div className="relative">
              <input
                id="password"
                type={showPassword ? "text" : "password"}
                value={form.password}
                onChange={(e) => handleChange("password", e.target.value)}
                placeholder="Min. 8 car., 1 majuscule, 1 chiffre"
                required
                className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 pr-10 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                autoComplete="new-password"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                aria-label={
                  showPassword ? "Masquer le mot de passe" : "Afficher le mot de passe"
                }
              >
                {showPassword ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </button>
            </div>
            {form.password.length > 0 && form.password.length < 8 && (
              <p className="mt-1 text-xs text-red-600">
                Minimum 8 caracteres
              </p>
            )}
          </div>

          <div>
            <label
              htmlFor="role"
              className="mb-1 block text-sm font-medium text-gray-700"
            >
              Role *
            </label>
            <select
              id="role"
              value={form.role}
              onChange={(e) => handleChange("role", e.target.value)}
              className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            >
              {ROLE_OPTIONS.map((r) => (
                <option key={r.value} value={r.value}>
                  {r.label}
                </option>
              ))}
            </select>
          </div>

          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={onClose}>
              Annuler
            </Button>
            <Button
              type="submit"
              disabled={!isValid || submitting}
              loading={submitting}
            >
              {submitting ? "Creation..." : "Creer l'utilisateur"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Page                                                          */
/* ------------------------------------------------------------------ */

export default function AdminUsersPage() {
  const { toast } = useToast();
  const {
    data,
    error: swrError,
    isLoading,
    mutate,
  } = useSWR<AdminUserListResponse>("/admin/users");

  const [showCreate, setShowCreate] = useState(false);
  const [deactivateTarget, setDeactivateTarget] = useState<AdminUser | null>(null);
  const [deactivating, setDeactivating] = useState(false);
  const [editingRole, setEditingRole] = useState<number | null>(null);

  const handleDeactivate = async () => {
    if (!deactivateTarget) return;
    setDeactivating(true);
    try {
      await fetchJson(`/admin/users/${deactivateTarget.id}`, {
        method: "DELETE",
      });
      toast("Utilisateur desactive", "success");
      mutate();
    } catch (err) {
      toast(
        err instanceof Error ? err.message : "Erreur lors de la desactivation",
        "error"
      );
    } finally {
      setDeactivating(false);
      setDeactivateTarget(null);
    }
  };

  const handleRoleChange = async (userId: number, newRole: string) => {
    try {
      await fetchJson(`/admin/users/${userId}`, {
        method: "PATCH",
        body: JSON.stringify({ role: newRole }),
      });
      toast("Role mis a jour", "success");
      mutate();
    } catch (err) {
      toast(
        err instanceof Error ? err.message : "Erreur lors de la mise a jour",
        "error"
      );
    } finally {
      setEditingRole(null);
    }
  };

  if (isLoading) {
    return (
      <PageLayout
        title="Utilisateurs"
        breadcrumb={[
          { label: "Admin", href: "/admin" },
          { label: "Utilisateurs" },
        ]}
      >
        <LoadingState text="Chargement des utilisateurs..." />
      </PageLayout>
    );
  }

  if (swrError) {
    return (
      <PageLayout
        title="Utilisateurs"
        breadcrumb={[
          { label: "Admin", href: "/admin" },
          { label: "Utilisateurs" },
        ]}
      >
        <ErrorState
          message={swrError?.message ?? "Impossible de charger les utilisateurs"}
          onRetry={() => mutate()}
        />
      </PageLayout>
    );
  }

  const users = data?.users ?? [];

  return (
    <PageLayout
      title="Gestion des utilisateurs"
      description="Ajoutez, modifiez ou desactivez les utilisateurs de votre magasin."
      breadcrumb={[
        { label: "Admin", href: "/admin" },
        { label: "Utilisateurs" },
      ]}
      actions={
        <Button onClick={() => setShowCreate(true)}>
          <Plus className="h-4 w-4 mr-1" />
          Ajouter un utilisateur
        </Button>
      }
    >
      {users.length === 0 ? (
        <EmptyState
          title="Aucun utilisateur"
          description="Ajoutez votre premier utilisateur pour commencer."
          icon={Users}
          action={
            <Button onClick={() => setShowCreate(true)}>
              <Plus className="h-4 w-4 mr-1" />
              Ajouter un utilisateur
            </Button>
          }
        />
      ) : (
        <div className="rounded-xl border border-border bg-bg-card shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-text-secondary">
                <th className="px-4 py-3 text-left font-medium">Email</th>
                <th className="px-4 py-3 text-left font-medium">Role</th>
                <th className="px-4 py-3 text-left font-medium">
                  Date de creation
                </th>
                <th className="px-4 py-3 text-center font-medium">Statut</th>
                <th className="px-4 py-3 text-right font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr
                  key={user.id}
                  className="border-b last:border-0 hover:bg-gray-50 transition-colors"
                >
                  <td className="px-4 py-3 font-medium text-gray-900">
                    {user.email}
                  </td>
                  <td className="px-4 py-3">
                    {editingRole === user.id ? (
                      <select
                        value={user.role}
                        onChange={(e) =>
                          handleRoleChange(user.id, e.target.value)
                        }
                        onBlur={() => setEditingRole(null)}
                        autoFocus
                        className="rounded-lg border border-gray-300 bg-white px-2 py-1 text-xs outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                      >
                        {ROLE_OPTIONS.map((r) => (
                          <option key={r.value} value={r.value}>
                            {r.label}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <button
                        onClick={() => setEditingRole(user.id)}
                        className="cursor-pointer"
                        title="Cliquer pour modifier le role"
                        aria-label={`Modifier le role de ${user.email}`}
                      >
                        {roleBadge(user.role)}
                      </button>
                    )}
                  </td>
                  <td className="px-4 py-3 text-text-secondary">
                    {user.created_at ? formatDateTime(user.created_at) : "-"}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span
                      className={cn(
                        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
                        user.is_active
                          ? "bg-emerald-50 text-emerald-700"
                          : "bg-red-50 text-red-700"
                      )}
                    >
                      {user.is_active ? "Actif" : "Desactive"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    {user.is_active && (
                      <button
                        onClick={() => setDeactivateTarget(user)}
                        className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-xs text-red-600 hover:bg-red-50 transition-colors"
                        aria-label={`Desactiver ${user.email}`}
                        title="Desactiver cet utilisateur"
                      >
                        <UserX className="h-3.5 w-3.5" />
                        Desactiver
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <CreateUserDialog
        open={showCreate}
        onClose={() => setShowCreate(false)}
        onCreated={() => mutate()}
      />

      <ConfirmDialog
        open={!!deactivateTarget}
        title="Desactiver l'utilisateur"
        message={`Etes-vous sur de vouloir desactiver ${deactivateTarget?.email ?? ""} ? L'utilisateur ne pourra plus se connecter.`}
        confirmLabel={deactivating ? "Desactivation..." : "Desactiver"}
        danger
        onConfirm={handleDeactivate}
        onCancel={() => setDeactivateTarget(null)}
      />
    </PageLayout>
  );
}
