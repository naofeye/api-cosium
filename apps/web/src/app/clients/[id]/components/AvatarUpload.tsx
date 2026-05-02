"use client";

import Image from "next/image";
import { useRef, useState } from "react";
import { Camera } from "lucide-react";
import { useToast } from "@/components/ui/Toast";
import { CopyButton } from "@/components/ui/CopyButton";
import { InlineEdit } from "@/components/ui/InlineEdit";
import { fetchJson, API_BASE } from "@/lib/api";
import { csrfHeaders } from "@/lib/csrf";

interface AvatarUploadProps {
  clientId: string;
  firstName: string;
  lastName: string;
  avatarUrl: string | null;
  email: string | null;
  phone: string | null;
  address: string | null;
  onUploaded: () => void;
}

export function AvatarUpload({
  clientId,
  firstName,
  lastName,
  avatarUrl,
  email,
  phone,
  address,
  onUploaded,
}: AvatarUploadProps) {
  const { toast } = useToast();

  const handleInlineSave = async (field: string, newValue: string) => {
    await fetchJson(`/clients/${clientId}`, {
      method: "PUT",
      body: JSON.stringify({ [field]: newValue || null }),
    });
    toast("Mis a jour", "success");
    onUploaded();
  };
  const avatarInputRef = useRef<HTMLInputElement>(null);
  const [uploadingAvatar, setUploadingAvatar] = useState(false);

  const handleAvatarUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const allowed = ["image/jpeg", "image/png", "image/jpg"];
    if (!allowed.includes(file.type)) {
      toast("Le fichier doit etre une image (JPG ou PNG).", "error");
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      toast("L'image ne doit pas depasser 5 Mo.", "error");
      return;
    }
    setUploadingAvatar(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const response = await fetch(`${API_BASE}/clients/${clientId}/avatar`, {
        method: "POST",
        body: formData,
        credentials: "include",
        headers: { ...csrfHeaders("POST") },
      });
      if (!response.ok) {
        let msg = "Impossible de mettre a jour l'avatar.";
        try {
          const body = await response.json();
          msg = body?.message || body?.detail || msg;
        } catch {
          // Non-JSON response
        }
        throw new Error(msg);
      }
      toast("Avatar mis a jour", "success");
      onUploaded();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Erreur", "error");
    } finally {
      setUploadingAvatar(false);
      if (avatarInputRef.current) avatarInputRef.current.value = "";
    }
  };

  return (
    <div className="flex items-center gap-4 mb-6">
      <div className="relative group">
        {avatarUrl ? (
          <Image
            src={`${API_BASE}/clients/${clientId}/avatar`}
            alt={`${firstName} ${lastName}`}
            width={64}
            height={64}
            className="h-16 w-16 rounded-full object-cover border-2 border-border"
            unoptimized
          />
        ) : (
          <div className="h-16 w-16 rounded-full bg-blue-100 flex items-center justify-center text-xl font-bold text-blue-700 border-2 border-border">
            {(firstName?.[0] || "").toUpperCase()}
            {(lastName?.[0] || "").toUpperCase()}
          </div>
        )}
        <button
          onClick={() => avatarInputRef.current?.click()}
          disabled={uploadingAvatar}
          className="absolute inset-0 rounded-full bg-black/40 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
          aria-label="Changer l'avatar"
        >
          <Camera className="h-5 w-5 text-white" />
        </button>
        <input
          ref={avatarInputRef}
          type="file"
          accept="image/jpeg,image/png"
          className="hidden"
          onChange={handleAvatarUpload}
        />
      </div>
      <div>
        <h2 className="text-lg font-semibold text-text-primary">
          {firstName} {lastName}
        </h2>
        <p className="text-sm text-text-secondary inline-flex items-center gap-1">
          <InlineEdit
            value={email || ""}
            onSave={(v) => handleInlineSave("email", v)}
            type="email"
            placeholder="email@exemple.com"
            emptyLabel="Ajouter un email"
            displayClassName="text-sm text-text-secondary"
          />
          {email && <CopyButton text={email} label="l'email" />}
        </p>
        <p className="text-sm text-text-secondary inline-flex items-center gap-1">
          <InlineEdit
            value={phone || ""}
            onSave={(v) => handleInlineSave("phone", v)}
            type="tel"
            placeholder="06 12 34 56 78"
            emptyLabel="Ajouter un telephone"
            displayClassName="text-sm text-text-secondary"
          />
          {phone && <CopyButton text={phone} label="le telephone" />}
        </p>
        <p className="text-sm text-text-secondary inline-flex items-center gap-1">
          <InlineEdit
            value={address || ""}
            onSave={(v) => handleInlineSave("address", v)}
            type="text"
            placeholder="12 rue de la Paix, 75001 Paris"
            emptyLabel="Ajouter une adresse"
            displayClassName="text-sm text-text-secondary"
          />
        </p>
      </div>
    </div>
  );
}
