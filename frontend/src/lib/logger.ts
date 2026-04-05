/**
 * Production-safe logger.
 * In development, logs to console. In production, silenced (or can be wired to a remote service).
 */
const isDev = process.env.NODE_ENV === "development";

export const logger = {
  error(message: string, ...args: unknown[]): void {
    if (isDev) {
      // eslint-disable-next-line no-console
      console.error(message, ...args);
    }
  },
  warn(message: string, ...args: unknown[]): void {
    if (isDev) {
      // eslint-disable-next-line no-console
      console.warn(message, ...args);
    }
  },
  info(message: string, ...args: unknown[]): void {
    if (isDev) {
      // eslint-disable-next-line no-console
      console.info(message, ...args);
    }
  },
};
