-- Migration: Remove unused fields from users table
-- Date: 2024-01-11
-- Description: Cleanup User model - keep only essential fields

-- ============================================================================
-- STEP 1: Drop foreign key constraints first
-- ============================================================================
ALTER TABLE users DROP CONSTRAINT IF EXISTS fk_users_department_id;
ALTER TABLE users DROP CONSTRAINT IF EXISTS fk_users_team_id;

-- ============================================================================
-- STEP 2: Drop indexes
-- ============================================================================
DROP INDEX IF EXISTS ix_users_codice_fiscale;

-- ============================================================================
-- STEP 3: Remove PROFILO BASE columns (keeping only first_name, last_name, avatar_path)
-- ============================================================================
ALTER TABLE users DROP COLUMN IF EXISTS job_title;
ALTER TABLE users DROP COLUMN IF EXISTS department_id;
ALTER TABLE users DROP COLUMN IF EXISTS team_id;
ALTER TABLE users DROP COLUMN IF EXISTS mobile;
ALTER TABLE users DROP COLUMN IF EXISTS citta;
ALTER TABLE users DROP COLUMN IF EXISTS indirizzo;
ALTER TABLE users DROP COLUMN IF EXISTS cv_file;
ALTER TABLE users DROP COLUMN IF EXISTS birth_date;

-- ============================================================================
-- STEP 4: Remove HR/CONTRATTO columns (keeping only assignment_ai_notes)
-- ============================================================================
ALTER TABLE users DROP COLUMN IF EXISTS hired_at;
ALTER TABLE users DROP COLUMN IF EXISTS contract_type;
ALTER TABLE users DROP COLUMN IF EXISTS contract_file;
ALTER TABLE users DROP COLUMN IF EXISTS skills;
ALTER TABLE users DROP COLUMN IF EXISTS languages;
ALTER TABLE users DROP COLUMN IF EXISTS hr_notes;
ALTER TABLE users DROP COLUMN IF EXISTS work_schedule;
ALTER TABLE users DROP COLUMN IF EXISTS development_plan;
ALTER TABLE users DROP COLUMN IF EXISTS accounts;

-- ============================================================================
-- STEP 5: Remove DATI FISCALI columns
-- ============================================================================
ALTER TABLE users DROP COLUMN IF EXISTS codice_fiscale;
ALTER TABLE users DROP COLUMN IF EXISTS partita_iva;
ALTER TABLE users DROP COLUMN IF EXISTS documento_tipo;
ALTER TABLE users DROP COLUMN IF EXISTS documento_numero;
ALTER TABLE users DROP COLUMN IF EXISTS documento_scadenza;
ALTER TABLE users DROP COLUMN IF EXISTS documento_fronte_path;
ALTER TABLE users DROP COLUMN IF EXISTS documento_retro_path;
ALTER TABLE users DROP COLUMN IF EXISTS ral_annua;
ALTER TABLE users DROP COLUMN IF EXISTS stipendio_mensile_lordo;

-- ============================================================================
-- STEP 6: Remove ORDINE PROFESSIONALE columns
-- ============================================================================
ALTER TABLE users DROP COLUMN IF EXISTS ordine_name;
ALTER TABLE users DROP COLUMN IF EXISTS ordine_provincia;
ALTER TABLE users DROP COLUMN IF EXISTS ordine_iscrizione_date;
ALTER TABLE users DROP COLUMN IF EXISTS ordine_numero_iscrizione;

-- ============================================================================
-- STEP 7: Remove FORMAZIONE columns
-- ============================================================================
ALTER TABLE users DROP COLUMN IF EXISTS education_high_school;
ALTER TABLE users DROP COLUMN IF EXISTS education_degrees;
ALTER TABLE users DROP COLUMN IF EXISTS education_masters;
ALTER TABLE users DROP COLUMN IF EXISTS education_phd;
ALTER TABLE users DROP COLUMN IF EXISTS education_courses;
ALTER TABLE users DROP COLUMN IF EXISTS education_certifications;

-- ============================================================================
-- STEP 8: Remove ESPERIENZA & RICERCA columns
-- ============================================================================
ALTER TABLE users DROP COLUMN IF EXISTS has_clinical_research;
ALTER TABLE users DROP COLUMN IF EXISTS clinical_research_details;
ALTER TABLE users DROP COLUMN IF EXISTS has_scientific_publications;
ALTER TABLE users DROP COLUMN IF EXISTS scientific_publications_details;
ALTER TABLE users DROP COLUMN IF EXISTS has_teaching_experience;
ALTER TABLE users DROP COLUMN IF EXISTS teaching_experience_details;
ALTER TABLE users DROP COLUMN IF EXISTS work_experiences;
ALTER TABLE users DROP COLUMN IF EXISTS referee_contacts;

-- ============================================================================
-- STEP 9: Remove COMPETENZE columns
-- ============================================================================
ALTER TABLE users DROP COLUMN IF EXISTS technical_skills;
ALTER TABLE users DROP COLUMN IF EXISTS soft_skills;

-- ============================================================================
-- STEP 10: Remove FINANCE columns
-- ============================================================================
ALTER TABLE users DROP COLUMN IF EXISTS finance_notes;

-- ============================================================================
-- VERIFICATION: Show remaining columns
-- ============================================================================
-- Run this to verify:
-- SELECT column_name, data_type FROM information_schema.columns
-- WHERE table_name = 'users' ORDER BY ordinal_position;
