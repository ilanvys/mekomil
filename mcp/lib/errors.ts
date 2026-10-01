export type ErrorCode =
  | "UNKNOWN_CATEGORY"
  | "CATALOG_UNAVAILABLE"
  | "UNKNOWN_SKILL"
  | "UNKNOWN_FILE"
  | "INVALID_PART"
  | "UPSTREAM_UNAVAILABLE"
  | "FILE_TOO_LARGE"
  | "INVALID_UPSTREAM_CONTENT";

export class AppError extends Error {
  constructor(
    public readonly code: ErrorCode,
    message: string,
    public readonly recovery?: Record<string, unknown>,
  ) {
    super(message);
    this.name = "AppError";
  }
}

export function asAppError(error: unknown, fallback: AppError): AppError {
  return error instanceof AppError ? error : fallback;
}
