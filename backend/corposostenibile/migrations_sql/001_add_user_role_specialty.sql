-- Migration: Add role, specialty, is_external to users table
-- Date: 2024-01-11
-- Description: Adds explicit role and specialty fields for the new Team management system

-- Step 1: Create ENUM types (if they don't exist)
DO $$
BEGIN
    -- Create userroleenum type
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'userroleenum') THEN
        CREATE TYPE public.userroleenum AS ENUM (
            'admin',
            'team_leader',
            'professionista',
            'team_esterno'
        );
    END IF;

    -- Create userspecialtyenum type
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'userspecialtyenum') THEN
        CREATE TYPE public.userspecialtyenum AS ENUM (
            'amministrazione',
            'cco',
            'nutrizione',
            'psicologia',
            'coach',
            'nutrizionista',
            'psicologo'
        );
    END IF;
END $$;

-- Step 2: Add columns to users table
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS role public.userroleenum NOT NULL DEFAULT 'professionista',
    ADD COLUMN IF NOT EXISTS specialty public.userspecialtyenum,
    ADD COLUMN IF NOT EXISTS is_external BOOLEAN NOT NULL DEFAULT FALSE;

-- Step 3: Create indexes for faster queries
CREATE INDEX IF NOT EXISTS ix_users_role ON users(role);
CREATE INDEX IF NOT EXISTS ix_users_specialty ON users(specialty);

-- Step 4: Add comments
COMMENT ON COLUMN users.role IS 'Ruolo utente: admin, team_leader, professionista, team_esterno';
COMMENT ON COLUMN users.specialty IS 'Specializzazione: nutrizione, psicologia, coach, etc.';
COMMENT ON COLUMN users.is_external IS 'True se l''utente è un collaboratore esterno';

-- Step 5: Migrate existing data based on current flags
-- Set role = 'admin' for users with is_admin = true
UPDATE users SET role = 'admin' WHERE is_admin = TRUE;

-- Set is_external = true and role = 'team_esterno' for external users
-- (You may need to adjust this based on how external users are currently identified)

-- Set role = 'team_leader' for users who lead teams
UPDATE users u
SET role = 'team_leader'
WHERE EXISTS (
    SELECT 1 FROM teams t WHERE t.head_id = u.id
)
AND u.is_admin = FALSE;

-- Try to set specialty based on department name
UPDATE users u
SET specialty = CASE
    WHEN d.name ILIKE '%nutri%' THEN 'nutrizione'::public.userspecialtyenum
    WHEN d.name ILIKE '%psico%' THEN 'psicologia'::public.userspecialtyenum
    WHEN d.name ILIKE '%coach%' THEN 'coach'::public.userspecialtyenum
    WHEN d.name ILIKE '%admin%' OR d.name ILIKE '%cco%' THEN 'amministrazione'::public.userspecialtyenum
    ELSE NULL
END
FROM departments d
WHERE u.department_id = d.id
AND u.specialty IS NULL;

-- Verification query (run after migration to check results)
-- SELECT id, email, first_name, last_name, is_admin, role, specialty, is_external
-- FROM users
-- ORDER BY role, specialty;
