CREATE TABLE candidates (
    id UUID PRIMARY KEY REFERENCES auth.users (id),
    email TEXT UNIQUE NOT NULL,
    full_name TEXT,
    phone TEXT,
    cv_url TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE candidate_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id UUID REFERENCES candidates (id) ON DELETE CASCADE,
    experience JSONB,
    education JSONB,
    skills TEXT[],          -- skills extracted from CV or other sources
    cv_path TEXT,                    -- path or URL to stored CV
    skills_score NUMERIC,            -- matching score between job and profile skills
    context_score NUMERIC,           -- contextual score
    source TEXT CHECK (source IN ('candidate', 'recruiter')) DEFAULT 'candidate',
    location TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE recruiters (
    id UUID PRIMARY KEY REFERENCES auth.users (id),
    email TEXT UNIQUE NOT NULL,
    full_name TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recruiter_id UUID REFERENCES recruiters (id) ON DELETE SET NULL,
    name TEXT,
    website TEXT,
    email TEXT,
    logo_url TEXT,
    description TEXT
);

CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies (id) ON DELETE CASCADE,
    title TEXT,
    description TEXT,
    location TEXT,
    requirements TEXT[],
    education TEXT,
    contract_type TEXT,
    work_mode TEXT,
    salary_min NUMERIC,
    salary_max NUMERIC,
    salary_currency TEXT,
    skills TEXT[],
    is_active BOOLEAN DEFAULT TRUE,
    match_criteria JSONB,
    experience TEXT,
    deadline DATE,
    file_url TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID REFERENCES jobs (id) ON DELETE CASCADE,
    candidate_id UUID REFERENCES candidates (id) ON DELETE CASCADE,
    status TEXT DEFAULT 'pending',  -- accepted, rejected
    score NUMERIC,
    created_at TIMESTAMP DEFAULT NOW()
);
