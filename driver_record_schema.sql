-- ITADIAS Driver Record Schema
-- Creates driver_record schema with all required tables for driver management system

-- Create schema if not exists
CREATE SCHEMA IF NOT EXISTS driver_record;

-- Create driver_records table
CREATE TABLE driver_record.driver_records (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id uuid NOT NULL REFERENCES identity.candidates(id),
    licence_number text UNIQUE NOT NULL,
    christian_names text NOT NULL,
    surname text NOT NULL,
    address text NOT NULL,
    dob date NOT NULL,
    photo_url text,
    signature_url text,
    licence_type text CHECK (licence_type IN ('Provisional','Class B','Class C','PPV','Special')),
    status text CHECK (status IN ('Issued','Suspended','Expired','Revoked')),
    certificate_of_competency_no text,
    application_date date NOT NULL,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- Create theory_attempts table
CREATE TABLE driver_record.theory_attempts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    driver_record_id uuid REFERENCES driver_record.driver_records(id),
    attempt_no int NOT NULL,
    module text NOT NULL,
    score int NOT NULL CHECK (score BETWEEN 0 AND 20),
    pass boolean NOT NULL,
    attempt_date date NOT NULL
);

-- Create yard_road_attempts table
CREATE TABLE driver_record.yard_road_attempts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    driver_record_id uuid REFERENCES driver_record.driver_records(id),
    test_type text CHECK (test_type IN ('Yard','Road')),
    visit_no int NOT NULL,
    attempt_date date NOT NULL,
    criteria jsonb NOT NULL, -- array of {criterion, major, minor, score}
    overall_result boolean NOT NULL
);

-- Create endorsements table
CREATE TABLE driver_record.endorsements (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    driver_record_id uuid REFERENCES driver_record.driver_records(id),
    endorsement_type text NOT NULL,
    issue_date date NOT NULL,
    expiry_date date
);

-- Create court_records table
CREATE TABLE driver_record.court_records (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    driver_record_id uuid REFERENCES driver_record.driver_records(id),
    judgment_date date NOT NULL,
    offence text NOT NULL,
    suspension_from date,
    suspension_to date,
    retest_required jsonb -- {written, yard, road, other}
);

-- Create audit_log table
CREATE TABLE driver_record.audit_log (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id uuid REFERENCES identity.candidates(id),
    actor_role text CHECK (actor_role IN ('dao','manager','rd')),
    action text NOT NULL,
    resource_type text NOT NULL,
    resource_id uuid,
    old_val jsonb,
    new_val jsonb,
    reason text,
    created_at timestamptz DEFAULT now()
);

-- Create indexes on licence_number, candidate_id, and foreign keys
CREATE INDEX idx_driver_records_licence_number ON driver_record.driver_records(licence_number);
CREATE INDEX idx_driver_records_candidate_id ON driver_record.driver_records(candidate_id);
CREATE INDEX idx_theory_attempts_driver_record_id ON driver_record.theory_attempts(driver_record_id);
CREATE INDEX idx_yard_road_attempts_driver_record_id ON driver_record.yard_road_attempts(driver_record_id);
CREATE INDEX idx_endorsements_driver_record_id ON driver_record.endorsements(driver_record_id);
CREATE INDEX idx_court_records_driver_record_id ON driver_record.court_records(driver_record_id);
CREATE INDEX idx_audit_log_actor_id ON driver_record.audit_log(actor_id);
CREATE INDEX idx_audit_log_resource_type ON driver_record.audit_log(resource_type);
CREATE INDEX idx_audit_log_resource_id ON driver_record.audit_log(resource_id);

-- Create trigger function to auto-update updated_at on driver_records
CREATE OR REPLACE FUNCTION driver_record.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add trigger to auto-update updated_at on driver_records
CREATE TRIGGER update_driver_records_updated_at 
    BEFORE UPDATE ON driver_record.driver_records 
    FOR EACH ROW 
    EXECUTE FUNCTION driver_record.update_updated_at_column();