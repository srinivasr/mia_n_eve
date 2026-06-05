import { writable } from 'svelte/store';

export type SetupStep = 'loading' | 'checks' | 'ready';

export interface CheckResult {
  mic: boolean | 'listening' | null;
  speakers: boolean | null;
  internet: boolean | null;
  ollama: boolean | null;
}

export interface CheckErrors {
  mic?: string;
  speakers?: string;
  internet?: string;
  ollama?: string;
}

export interface ConfigStatus {
  configured: boolean;
  key_valid: boolean | null;
  checks: CheckResult;
  check_errors: CheckErrors;
}

export const setupStep = writable<SetupStep>('loading');
export const configStatus = writable<ConfigStatus>({
  configured: false,
  key_valid: null,
  checks: { mic: null, speakers: null, internet: null, ollama: null },
  check_errors: {},
});
export const checkRunning = writable<string | null>(null);
export const wizardComplete = writable<boolean>(false);
