export type EnrollmentStep = "idle" | "enrolling" | "verifying" | "confirming-disable";

export interface MfaSetupResponse {
  secret: string;
  otpauth_uri: string;
  issuer: string;
}

export interface MfaStatusResponse {
  enabled: boolean;
}

export interface MfaBackupCodesResponse {
  codes: string[];
  remaining: number;
}

export interface MfaBackupCodesCountResponse {
  remaining: number;
}
