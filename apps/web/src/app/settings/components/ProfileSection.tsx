"use client";

import { User } from "lucide-react";

interface UserProfile {
  id: number;
  email: string;
  full_name?: string;
  role: string;
}

interface ProfileSectionProps {
  profile: UserProfile | null;
  editName: string;
  editEmail: string;
  onNameChange: (value: string) => void;
  onEmailChange: (value: string) => void;
  inputClasses: string;
}

export function ProfileSection({
  profile,
  editName,
  editEmail,
  onNameChange,
  onEmailChange,
  inputClasses,
}: ProfileSectionProps) {
  return (
    <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm mb-6">
      <div className="flex items-center gap-4 mb-6">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary text-white">
          <User className="h-6 w-6" />
        </div>
        <div>
          <h2 className="text-lg font-semibold text-text-primary">Profil utilisateur</h2>
          <p className="text-sm text-text-secondary">
            Gerez vos informations personnelles
          </p>
        </div>
      </div>

      <div className="max-w-md space-y-4">
        <div>
          <label htmlFor="profile-name" className="block text-sm font-medium text-text-secondary mb-1">
            Nom complet
          </label>
          <input
            id="profile-name"
            type="text"
            placeholder="Votre nom"
            value={editName}
            onChange={(e) => onNameChange(e.target.value)}
            className={inputClasses}
          />
        </div>
        <div>
          <label htmlFor="profile-email" className="block text-sm font-medium text-text-secondary mb-1">
            Adresse email
          </label>
          <input
            id="profile-email"
            type="email"
            placeholder="votre@email.com"
            value={editEmail}
            onChange={(e) => onEmailChange(e.target.value)}
            className={inputClasses}
          />
        </div>
        {profile && (
          <p className="text-xs text-text-secondary">
            Role : <span className="font-medium capitalize">{profile.role}</span>
          </p>
        )}
      </div>
    </div>
  );
}
