-- Recruitment Platform Database Schema
-- PostgreSQL 15+ with PostGIS extension

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "postgis";

-- Users table for authentication
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'recruiter',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Candidates table
CREATE TABLE candidates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    location GEOGRAPHY(POINT, 4326),
    resume_url TEXT,
    parsed_resume JSONB,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Job postings table
CREATE TABLE job_postings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    requirements JSONB NOT NULL,
    department VARCHAR(100) NOT NULL,
    location GEOGRAPHY(POINT, 4326),
    employment_type VARCHAR(50) NOT NULL,
    salary_range JSONB,
    status VARCHAR(50) DEFAULT 'active',
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Applications table
CREATE TABLE applications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    candidate_id UUID REFERENCES candidates(id),
    job_id UUID REFERENCES job_postings(id),
    status VARCHAR(50) DEFAULT 'applied',
    match_score DECIMAL(5,2),
    applied_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(candidate_id, job_id)
);

-- Application status history for audit trail
CREATE TABLE application_status_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    application_id UUID REFERENCES applications(id),
    previous_status VARCHAR(50),
    new_status VARCHAR(50) NOT NULL,
    changed_by UUID REFERENCES users(id),
    change_reason TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Skills taxonomy table
CREATE TABLE skills (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    category VARCHAR(50),
    synonyms TEXT[],
    created_at TIMESTAMP DEFAULT NOW()
);

-- Candidate skills mapping
CREATE TABLE candidate_skills (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    candidate_id UUID REFERENCES candidates(id),
    skill_id UUID REFERENCES skills(id),
    proficiency_level VARCHAR(20) DEFAULT 'intermediate',
    years_experience INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(candidate_id, skill_id)
);

-- Job requirements skills mapping
CREATE TABLE job_required_skills (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID REFERENCES job_postings(id),
    skill_id UUID REFERENCES skills(id),
    required_level VARCHAR(20) DEFAULT 'intermediate',
    min_years_experience INTEGER DEFAULT 0,
    is_mandatory BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(job_id, skill_id)
);

-- Test definitions
CREATE TABLE test_definitions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(200) NOT NULL,
    description TEXT,
    duration_minutes INTEGER NOT NULL,
    passing_score INTEGER DEFAULT 70,
    question_count INTEGER NOT NULL,
    is_adaptive BOOLEAN DEFAULT false,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- API keys for external integrations
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key_name VARCHAR(100) NOT NULL,
    api_key VARCHAR(255) UNIQUE NOT NULL,
    permissions JSONB NOT NULL,
    rate_limit INTEGER DEFAULT 1000,
    is_active BOOLEAN DEFAULT true,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    last_used_at TIMESTAMP
);

-- Audit log for security and compliance
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id UUID,
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_candidates_email ON candidates(email);
CREATE INDEX idx_candidates_status ON candidates(status);
CREATE INDEX idx_candidates_created_at ON candidates(created_at);
CREATE INDEX idx_candidates_location ON candidates USING GIST(location);

CREATE INDEX idx_job_postings_status ON job_postings(status);
CREATE INDEX idx_job_postings_department ON job_postings(department);
CREATE INDEX idx_job_postings_created_at ON job_postings(created_at);
CREATE INDEX idx_job_postings_location ON job_postings USING GIST(location);

CREATE INDEX idx_applications_candidate_id ON applications(candidate_id);
CREATE INDEX idx_applications_job_id ON applications(job_id);
CREATE INDEX idx_applications_status ON applications(status);
CREATE INDEX idx_applications_match_score ON applications(match_score);
CREATE INDEX idx_applications_applied_at ON applications(applied_at);

CREATE INDEX idx_application_status_history_application_id ON application_status_history(application_id);
CREATE INDEX idx_application_status_history_created_at ON application_status_history(created_at);

CREATE INDEX idx_candidate_skills_candidate_id ON candidate_skills(candidate_id);
CREATE INDEX idx_candidate_skills_skill_id ON candidate_skills(skill_id);

CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);

-- Insert some initial data
INSERT INTO users (email, password_hash, first_name, last_name, role) VALUES
('admin@recruitment.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj/VJWZFSxuS', 'Admin', 'User', 'admin'),
('recruiter@recruitment.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj/VJWZFSxuS', 'Jane', 'Recruiter', 'recruiter'),
('manager@recruitment.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj/VJWZFSxuS', 'John', 'Manager', 'hiring_manager');

-- Insert common skills
INSERT INTO skills (name, category, synonyms) VALUES
('Python', 'Programming', ARRAY['python', 'py']),
('JavaScript', 'Programming', ARRAY['js', 'javascript', 'node.js', 'nodejs']),
('React', 'Frontend', ARRAY['react.js', 'reactjs']),
('PostgreSQL', 'Database', ARRAY['postgres', 'psql']),
('Docker', 'DevOps', ARRAY['containerization']),
('AWS', 'Cloud', ARRAY['amazon web services', 'amazon aws']),
('Machine Learning', 'AI/ML', ARRAY['ml', 'artificial intelligence', 'ai']),
('FastAPI', 'Backend', ARRAY['fast api']),
('MongoDB', 'Database', ARRAY['mongo']),
('Redis', 'Database', ARRAY['cache', 'caching']);