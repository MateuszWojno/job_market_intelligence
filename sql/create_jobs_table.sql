-- Serialize schema initialization and weekly writes in this transaction.
SELECT pg_advisory_xact_lock(94176203);

DO $migration$
BEGIN
    IF to_regclass('public.job_offers') IS NULL
       AND to_regclass('public.nofluff_it_jobs_clean') IS NOT NULL THEN
        ALTER TABLE public.nofluff_it_jobs_clean RENAME TO job_offers;
    END IF;
END
$migration$;

CREATE TABLE IF NOT EXISTS public.job_offers (
    job_id text PRIMARY KEY,
    url text NOT NULL,
    title text,
    category text,
    workplace text,
    job_locations text,
    company text,
    company_size text,
    company_founded integer,
    company_locations text,
    salary_min numeric,
    salary_max numeric,
    salary_currency text,
    salary_period text,
    contract_type text,
    required_skills text,
    nice_to_have text,
    requirements text,
    offer_description text,
    responsibilities text,
    valid_until date,
    start_date text,
    scraped_at timestamp,
    start_asap boolean,
    start_date_parsed date,
    company_size_min integer,
    company_size_max integer,
    company_size_segment text,
    experience text,
    experience_years_min integer,
    salary_exchange_rate_to_pln double precision,
    salary_mid double precision,
    salary_min_pln_monthly double precision,
    salary_max_pln_monthly double precision,
    salary_mid_pln_monthly double precision,
    salary_normalization_eligible boolean,
    salary_analysis_eligible boolean,
    salary_exchange_rate_date date
);

DO $migration$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.job_offers'::regclass AND contype = 'p'
    ) THEN
        IF to_regclass('public.uq_nofluff_jobs_job_id') IS NOT NULL THEN
            ALTER TABLE public.job_offers ADD CONSTRAINT job_offers_pkey
                PRIMARY KEY USING INDEX uq_nofluff_jobs_job_id;
        ELSE
            ALTER TABLE public.job_offers ADD PRIMARY KEY (job_id);
        END IF;
    END IF;

    IF to_regclass('public.nofluff_it_jobs_clean') IS NULL THEN
        CREATE VIEW public.nofluff_it_jobs_clean AS SELECT * FROM public.job_offers;
    END IF;
END
$migration$;

CREATE TABLE IF NOT EXISTS public.offer_contract_types (
    job_id text REFERENCES public.job_offers(job_id) ON DELETE CASCADE,
    contract_type text NOT NULL,
    PRIMARY KEY (job_id, contract_type)
);
