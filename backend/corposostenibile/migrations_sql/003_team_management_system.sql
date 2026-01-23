-- Migration: Team Management System
-- Date: 2024-01-12
-- Description: Adds team_type, is_active to teams table, creates team_members association table

-- Step 1: Create TeamTypeEnum type
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'teamtypeenum') THEN
        CREATE TYPE public.teamtypeenum AS ENUM (
            'nutrizione',
            'coach',
            'psicologia'
        );
    END IF;
END $$;

-- Step 2: Add new columns to teams table
ALTER TABLE teams
    ADD COLUMN IF NOT EXISTS team_type public.teamtypeenum,
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;

-- Step 3: Make department_id nullable (for independent teams)
ALTER TABLE teams
    ALTER COLUMN department_id DROP NOT NULL;

-- Step 4: Create index for team_type
CREATE INDEX IF NOT EXISTS ix_teams_team_type ON teams(team_type);
CREATE INDEX IF NOT EXISTS ix_teams_is_active ON teams(is_active);

-- Step 5: Add comments
COMMENT ON COLUMN teams.team_type IS 'Tipo di team: nutrizione, coach, psicologia';
COMMENT ON COLUMN teams.is_active IS 'True se il team è attivo';

-- Step 6: Create team_members association table
CREATE TABLE IF NOT EXISTS team_members (
    team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    joined_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    PRIMARY KEY (team_id, user_id)
);

-- Step 7: Create indexes for team_members
CREATE INDEX IF NOT EXISTS ix_team_members_team_id ON team_members(team_id);
CREATE INDEX IF NOT EXISTS ix_team_members_user_id ON team_members(user_id);

-- Step 8: Drop old unique constraint (if exists) and create new one
-- First, check if the old constraint exists and drop it
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'uq_teams_department_name'
    ) THEN
        ALTER TABLE teams DROP CONSTRAINT uq_teams_department_name;
    END IF;
END $$;

-- Create new unique constraint on (team_type, name)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'uq_teams_type_name'
    ) THEN
        ALTER TABLE teams ADD CONSTRAINT uq_teams_type_name UNIQUE (team_type, name);
    END IF;
END $$;

-- Step 9: Add teams relationship to users (already exists via team_members)
-- The relationship is handled by SQLAlchemy via the team_members table

-- Verification queries (run after migration to check results)
-- SELECT * FROM teams;
-- SELECT * FROM team_members;
-- \d teams
-- \d team_members
