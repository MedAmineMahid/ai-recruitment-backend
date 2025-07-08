-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

CREATE TABLE public.applications (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  job_id uuid,
  candidate_id uuid,
  status text DEFAULT 'pending'::text,
  score numeric,
  created_at timestamp without time zone DEFAULT now(),
  global_score numeric,
  skill_score numeric,
  CONSTRAINT applications_pkey PRIMARY KEY (id),
  CONSTRAINT applications_candidate_id_fkey FOREIGN KEY (candidate_id) REFERENCES public.candidates(id),
  CONSTRAINT applications_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.jobs(id)
);
CREATE TABLE public.candidate_profiles (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  candidate_id uuid,
  experience jsonb,
  education jsonb,
  cv_path text,
  source text DEFAULT 'candidate'::text CHECK (source = ANY (ARRAY['candidate'::text, 'recruiter'::text])),
  location text,
  updated_at timestamp without time zone DEFAULT now(),
  cv text,
  skillner_skills ARRAY,
  py_skills ARRAY,
  added_skills ARRAY,
  title text,
  about text,
  linkedin text,
  website text,
  github text,
  cv_last_updated timestamp without time zone DEFAULT now(),
  certifications jsonb DEFAULT '[]'::jsonb,
  languages jsonb DEFAULT '[]'::jsonb,
  job_preferences jsonb DEFAULT '{}'::jsonb,
  CONSTRAINT candidate_profiles_pkey PRIMARY KEY (id),
  CONSTRAINT candidate_profiles_candidate_id_fkey FOREIGN KEY (candidate_id) REFERENCES public.candidates(id)
);
CREATE TABLE public.candidates (
  id uuid NOT NULL,
  email text NOT NULL UNIQUE,
  full_name text,
  phone text,
  cv_url text,
  created_at timestamp without time zone DEFAULT now(),
  CONSTRAINT candidates_pkey PRIMARY KEY (id),
  CONSTRAINT candidates_id_fkey FOREIGN KEY (id) REFERENCES auth.users(id)
);
CREATE TABLE public.companies (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  recruiter_id uuid,
  name text,
  website text,
  email text,
  logo_url text,
  description text,
  CONSTRAINT companies_pkey PRIMARY KEY (id),
  CONSTRAINT companies_recruiter_id_fkey FOREIGN KEY (recruiter_id) REFERENCES public.recruiters(id)
);
CREATE TABLE public.jobs (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  recruiter_id uuid,
  company_id uuid,
  title text,
  description text,
  location text,
  requirements ARRAY,
  education text,
  file_url text,
  created_at timestamp without time zone DEFAULT now(),
  contract_type text,
  work_mode text,
  salary_min numeric,
  salary_max numeric,
  salary_currency text DEFAULT 'EUR'::text,
  skills ARRAY,
  is_active boolean DEFAULT true,
  match_criteria jsonb,
  CONSTRAINT jobs_pkey PRIMARY KEY (id),
  CONSTRAINT jobs_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id),
  CONSTRAINT jobs_recruiter_id_fkey FOREIGN KEY (recruiter_id) REFERENCES public.recruiters(id)
);
CREATE TABLE public.recruiters (
  id uuid NOT NULL,
  email text NOT NULL UNIQUE,
  full_name text,
  created_at timestamp without time zone DEFAULT now(),
  CONSTRAINT recruiters_pkey PRIMARY KEY (id),
  CONSTRAINT recruiters_id_fkey FOREIGN KEY (id) REFERENCES auth.users(id)
);




CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sender_id UUID NOT NULL, -- Can be candidate or recruiter
    receiver_id UUID NOT NULL, -- Can be candidate or recruiter
    job_id UUID REFERENCES jobs (id) ON DELETE CASCADE, -- Optional: link message to a specific job application
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE public.candidate_job_matches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    candidate_id UUID REFERENCES public.candidates(id) ON DELETE CASCADE,
    job_id UUID REFERENCES public.jobs(id) ON DELETE CASCADE,
    match_score NUMERIC(5, 2) NOT NULL,
    sbert_similarity NUMERIC(5, 2),
    skill2vec_similarity NUMERIC(5, 2),
    matched_skills JSONB,
    candidate_skills JSONB,
    job_skills JSONB,
    prediction TEXT,
    match_percentage NUMERIC(5, 2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE public.candidate_job_matches ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Candidates can view their own job matches" ON public.candidate_job_matches
FOR SELECT TO authenticated USING (candidate_id = auth.uid());

CREATE POLICY "Candidates can insert their own job matches" ON public.candidate_job_matches
FOR INSERT TO authenticated WITH CHECK (candidate_id = auth.uid());

CREATE POLICY "Candidates can update their own job matches" ON public.candidate_job_matches
FOR UPDATE TO authenticated USING (candidate_id = auth.uid());

CREATE POLICY "Candidates can delete their own job matches" ON public.candidate_job_matches
FOR DELETE TO authenticated USING (candidate_id = auth.uid());

CREATE POLICY "Allow anon insert if authenticated" ON public.candidate_job_matches
FOR INSERT TO anon WITH CHECK (auth.role() = 'authenticated');

CREATE POLICY "Allow anon update if authenticated" ON public.candidate_job_matches
FOR UPDATE TO anon USING (auth.role() = 'authenticated');