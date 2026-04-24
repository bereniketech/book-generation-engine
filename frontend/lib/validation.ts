/**
 * Re-export of generated schema.
 *
 * This file re-exports schemas from frontend/lib/generated/job_schema.ts,
 * which is auto-generated from app/domain/validation_schemas.py.
 *
 * Do not add constraints here — they come from the backend as the single
 * source of truth. To update constraints, edit app/domain/validation_schemas.py
 * and regenerate by running: python scripts/generate_schema.py
 *
 * @deprecated Import directly from "./generated/job_schema.ts" instead
 */

export {
  JobCreateSchema,
  LLMProviderSchema,
  ImageProviderSchema,
  LLM_PROVIDERS,
  IMAGE_PROVIDERS,
  type JobCreateInput,
  type LLMProviderInput,
  type ImageProviderInput,
} from "./generated/job_schema";
