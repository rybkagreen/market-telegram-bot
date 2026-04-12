--
-- PostgreSQL database dump
--

\restrict KbqBct9beXuPBp0JjxRPbSKlZPHLoky50afas5aSt9v7vVwa7uMnQJdM4LekvCN

-- Dumped from database version 16.13
-- Dumped by pg_dump version 16.13

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: -
--

-- *not* creating schema, since initdb creates it


--
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON SCHEMA public IS '';


--
-- Name: disputereason; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.disputereason AS ENUM (
    'post_removed_early',
    'bot_kicked',
    'advertiser_complaint'
);


--
-- Name: disputeresolution; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.disputeresolution AS ENUM (
    'owner_fault',
    'advertiser_fault',
    'technical',
    'partial'
);


--
-- Name: disputestatus; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.disputestatus AS ENUM (
    'open',
    'owner_explained',
    'resolved'
);


--
-- Name: payoutstatus; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.payoutstatus AS ENUM (
    'pending',
    'processing',
    'paid',
    'rejected',
    'cancelled'
);


--
-- Name: placementstatus; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.placementstatus AS ENUM (
    'pending_owner',
    'counter_offer',
    'pending_payment',
    'escrow',
    'published',
    'failed',
    'failed_permissions',
    'refunded',
    'cancelled'
);


--
-- Name: publicationformat; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.publicationformat AS ENUM (
    'post_24h',
    'post_48h',
    'post_7d',
    'pin_24h',
    'pin_48h'
);


--
-- Name: reputationaction; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.reputationaction AS ENUM (
    'publication',
    'review_5star',
    'review_4star',
    'review_3star',
    'review_2star',
    'review_1star',
    'cancel_before_escrow',
    'cancel_after_confirm',
    'cancel_systematic',
    'reject_invalid_1',
    'reject_invalid_2',
    'reject_invalid_3',
    'reject_frequent',
    'dispute_owner_fault',
    'recovery_30days',
    'ban_reset'
);


--
-- Name: transactiontype; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.transactiontype AS ENUM (
    'topup',
    'escrow_freeze',
    'escrow_release',
    'platform_fee',
    'refund_full',
    'refund_partial',
    'cancel_penalty',
    'owner_cancel_compensation',
    'payout',
    'payout_fee',
    'credits_buy',
    'failed_permissions_refund',
    'bonus',
    'spend',
    'commission',
    'refund',
    'ndfl_withholding'
);


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: acts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.acts (
    id integer NOT NULL,
    placement_request_id integer NOT NULL,
    act_number character varying(20) NOT NULL,
    act_date timestamp with time zone DEFAULT now() NOT NULL,
    pdf_path character varying(255) NOT NULL,
    generated_at timestamp with time zone DEFAULT now() NOT NULL,
    meta_json jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    contract_id integer,
    act_type character varying(10) DEFAULT 'income'::character varying NOT NULL,
    sign_status character varying(15) DEFAULT 'draft'::character varying NOT NULL,
    signed_at timestamp with time zone,
    sign_method character varying(20),
    ip_hash character varying(64),
    user_agent_hash character varying(64)
);


--
-- Name: acts_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.acts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: acts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.acts_id_seq OWNED BY public.acts.id;


--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: audit_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_logs (
    id bigint NOT NULL,
    user_id bigint,
    action character varying(20) NOT NULL,
    resource_type character varying(50) NOT NULL,
    resource_id integer,
    target_user_id bigint,
    ip_address character varying(45),
    user_agent character varying(500),
    extra json,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: audit_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.audit_logs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: audit_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.audit_logs_id_seq OWNED BY public.audit_logs.id;


--
-- Name: badge_achievements; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.badge_achievements (
    id integer NOT NULL,
    badge_id integer NOT NULL,
    achievement_type character varying(64) NOT NULL,
    threshold double precision NOT NULL,
    description text NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: badge_achievements_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.badge_achievements_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: badge_achievements_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.badge_achievements_id_seq OWNED BY public.badge_achievements.id;


--
-- Name: badges; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.badges (
    id integer NOT NULL,
    code character varying(64) NOT NULL,
    name character varying(128) NOT NULL,
    description text NOT NULL,
    icon_emoji character varying(8) NOT NULL,
    xp_reward integer DEFAULT 0 NOT NULL,
    credits_reward integer DEFAULT 0 NOT NULL,
    category character varying(16) NOT NULL,
    condition_type character varying(32) NOT NULL,
    condition_value double precision DEFAULT '0'::double precision NOT NULL,
    is_rare boolean DEFAULT false NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: badges_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.badges_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: badges_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.badges_id_seq OWNED BY public.badges.id;


--
-- Name: categories; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.categories (
    id integer NOT NULL,
    name_ru character varying(128) NOT NULL,
    emoji character varying(8) DEFAULT '🔖'::character varying NOT NULL,
    slug character varying(64) NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    sort_order integer DEFAULT 0 NOT NULL
);


--
-- Name: categories_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.categories_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: categories_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.categories_id_seq OWNED BY public.categories.id;


--
-- Name: channel_mediakits; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.channel_mediakits (
    id integer NOT NULL,
    channel_id integer NOT NULL,
    description text,
    audience_description text,
    avg_post_reach integer NOT NULL,
    views_count integer NOT NULL,
    downloads_count integer NOT NULL,
    is_published boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: channel_mediakits_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.channel_mediakits_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: channel_mediakits_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.channel_mediakits_id_seq OWNED BY public.channel_mediakits.id;


--
-- Name: channel_settings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.channel_settings (
    channel_id integer NOT NULL,
    price_per_post numeric(10,2) DEFAULT '1000'::numeric NOT NULL,
    allow_format_post_24h boolean DEFAULT true NOT NULL,
    allow_format_post_48h boolean DEFAULT true NOT NULL,
    allow_format_post_7d boolean DEFAULT false NOT NULL,
    allow_format_pin_24h boolean DEFAULT false NOT NULL,
    allow_format_pin_48h boolean DEFAULT false NOT NULL,
    max_posts_per_day integer DEFAULT 2 NOT NULL,
    max_posts_per_week integer DEFAULT 10 NOT NULL,
    publish_start_time time without time zone NOT NULL,
    publish_end_time time without time zone NOT NULL,
    break_start_time time without time zone,
    break_end_time time without time zone,
    auto_accept_enabled boolean DEFAULT false NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: click_tracking; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.click_tracking (
    id integer NOT NULL,
    placement_request_id integer NOT NULL,
    short_code character varying(16) NOT NULL,
    clicked_at timestamp with time zone DEFAULT now() NOT NULL,
    user_agent character varying(512)
);


--
-- Name: contract_signatures; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contract_signatures (
    id integer NOT NULL,
    contract_id integer NOT NULL,
    user_id integer NOT NULL,
    telegram_id bigint NOT NULL,
    role character varying(20) NOT NULL,
    legal_status character varying(30) NOT NULL,
    signed_at timestamp with time zone DEFAULT now() NOT NULL,
    signature_method character varying(20) NOT NULL,
    document_hash character varying(64) NOT NULL,
    template_version character varying(20) DEFAULT '1.0'::character varying NOT NULL,
    ip_address character varying(45),
    user_agent character varying(500)
);


--
-- Name: contract_signatures_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.contract_signatures_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: contract_signatures_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.contract_signatures_id_seq OWNED BY public.contract_signatures.id;


--
-- Name: contracts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contracts (
    id integer NOT NULL,
    user_id integer NOT NULL,
    contract_type character varying(30) NOT NULL,
    contract_status character varying(20) DEFAULT 'draft'::character varying NOT NULL,
    placement_request_id integer,
    legal_status_snapshot jsonb,
    template_version character varying(20) DEFAULT '1.0'::character varying NOT NULL,
    pdf_file_path character varying(500),
    pdf_telegram_file_id character varying(200),
    signature_method character varying(20),
    signature_ip character varying(45),
    signed_at timestamp with time zone,
    expires_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    kep_requested boolean DEFAULT false NOT NULL,
    kep_request_email character varying(254),
    role character varying(20)
);


--
-- Name: contracts_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.contracts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: contracts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.contracts_id_seq OWNED BY public.contracts.id;


--
-- Name: document_counters; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.document_counters (
    prefix character varying(4) NOT NULL,
    year integer NOT NULL,
    current_seq integer DEFAULT 0 NOT NULL
);


--
-- Name: document_uploads; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.document_uploads (
    id integer NOT NULL,
    user_id integer NOT NULL,
    original_filename character varying(255) NOT NULL,
    stored_path character varying(500) NOT NULL,
    file_type character varying(16) NOT NULL,
    file_size integer NOT NULL,
    document_type character varying(32) NOT NULL,
    image_quality_score numeric(3,2),
    quality_issues text,
    is_readable boolean DEFAULT false NOT NULL,
    ocr_text text,
    ocr_confidence numeric(3,2),
    extracted_inn character varying(20),
    extracted_kpp character varying(20),
    extracted_ogrn character varying(20),
    extracted_ogrnip character varying(20),
    extracted_name character varying(500),
    validation_status character varying(16) DEFAULT 'pending'::character varying NOT NULL,
    validation_details text,
    error_message text,
    processing_started_at timestamp with time zone,
    completed_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: document_uploads_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.document_uploads_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: document_uploads_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.document_uploads_id_seq OWNED BY public.document_uploads.id;


--
-- Name: invoices; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.invoices (
    id integer NOT NULL,
    user_id integer NOT NULL,
    invoice_number character varying(20) NOT NULL,
    amount_rub numeric(12,2) NOT NULL,
    vat_amount numeric(12,2) DEFAULT '0'::numeric NOT NULL,
    status character varying(20) DEFAULT 'draft'::character varying NOT NULL,
    pdf_path character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    placement_request_id integer,
    contract_id integer
);


--
-- Name: invoices_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.invoices_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: invoices_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.invoices_id_seq OWNED BY public.invoices.id;


--
-- Name: kudir_records; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.kudir_records (
    id integer NOT NULL,
    quarter character varying(10) NOT NULL,
    entry_number integer NOT NULL,
    operation_date timestamp with time zone DEFAULT now() NOT NULL,
    description character varying(255) NOT NULL,
    income_amount numeric(12,2) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    operation_type character varying(10) DEFAULT 'income'::character varying NOT NULL,
    expense_category character varying(30),
    expense_amount numeric(12,2)
);


--
-- Name: kudir_records_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.kudir_records_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: kudir_records_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.kudir_records_id_seq OWNED BY public.kudir_records.id;


--
-- Name: legal_profiles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.legal_profiles (
    id integer NOT NULL,
    user_id bigint NOT NULL,
    legal_status character varying(30) NOT NULL,
    inn character varying(300),
    kpp character varying(9),
    ogrn character varying(15),
    ogrnip character varying(15),
    legal_name character varying(500),
    address text,
    tax_regime character varying(20),
    bank_name character varying(200),
    bank_account character varying(300),
    bank_bik character varying(9),
    bank_corr_account character varying(300),
    yoomoney_wallet character varying(300),
    passport_series character varying(300),
    passport_number character varying(300),
    passport_issued_by character varying(1000),
    passport_issue_date date,
    inn_scan_file_id character varying(500),
    passport_scan_file_id character varying(500),
    self_employed_cert_file_id character varying(500),
    company_doc_file_id character varying(500),
    is_verified boolean DEFAULT false NOT NULL,
    verified_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    inn_hash character varying(64)
);


--
-- Name: legal_profiles_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.legal_profiles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: legal_profiles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.legal_profiles_id_seq OWNED BY public.legal_profiles.id;


--
-- Name: mailing_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.mailing_logs (
    id integer NOT NULL,
    placement_request_id integer,
    campaign_id integer,
    chat_id integer,
    chat_telegram_id bigint NOT NULL,
    status character varying(32) DEFAULT 'pending'::character varying NOT NULL,
    message_id bigint,
    cost numeric(12,2) NOT NULL,
    scheduled_at timestamp with time zone,
    sent_at timestamp with time zone,
    error_msg text,
    retry_count integer DEFAULT 0 NOT NULL,
    meta_json jsonb,
    rejection_reason text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: ord_registrations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ord_registrations (
    id integer NOT NULL,
    placement_request_id integer NOT NULL,
    contract_id integer,
    advertiser_ord_id character varying(100),
    creative_ord_id character varying(100),
    erid character varying(100),
    ord_provider character varying(50) DEFAULT 'default'::character varying NOT NULL,
    status character varying(20) DEFAULT 'pending'::character varying NOT NULL,
    registered_at timestamp with time zone,
    token_received_at timestamp with time zone,
    reported_at timestamp with time zone,
    error_message text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    yandex_request_id character varying(128),
    platform_ord_id character varying(128),
    contract_ord_id character varying(128)
);


--
-- Name: ord_registrations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.ord_registrations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: ord_registrations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.ord_registrations_id_seq OWNED BY public.ord_registrations.id;


--
-- Name: payout_requests; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.payout_requests (
    id integer NOT NULL,
    owner_id integer NOT NULL,
    gross_amount numeric(12,2) NOT NULL,
    fee_amount numeric(12,2) NOT NULL,
    net_amount numeric(12,2) NOT NULL,
    status public.payoutstatus NOT NULL,
    requisites character varying(512) NOT NULL,
    admin_id integer,
    processed_at timestamp with time zone,
    rejection_reason text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    ndfl_withheld numeric(12,2) DEFAULT '0'::numeric,
    npd_receipt_number character varying(64),
    npd_receipt_date timestamp with time zone,
    npd_status character varying(20) DEFAULT 'pending'::character varying NOT NULL
);


--
-- Name: payout_requests_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.payout_requests_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: payout_requests_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.payout_requests_id_seq OWNED BY public.payout_requests.id;


--
-- Name: placement_disputes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.placement_disputes (
    id integer NOT NULL,
    placement_request_id integer NOT NULL,
    advertiser_id integer NOT NULL,
    owner_id integer NOT NULL,
    reason public.disputereason NOT NULL,
    status public.disputestatus NOT NULL,
    owner_explanation text,
    advertiser_comment text,
    resolution public.disputeresolution,
    resolution_comment text,
    admin_id integer,
    resolved_at timestamp with time zone,
    advertiser_refund_pct double precision,
    owner_payout_pct double precision,
    expires_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: placement_disputes_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.placement_disputes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: placement_disputes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.placement_disputes_id_seq OWNED BY public.placement_disputes.id;


--
-- Name: placement_requests; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.placement_requests (
    id integer NOT NULL,
    advertiser_id integer NOT NULL,
    owner_id integer NOT NULL,
    channel_id integer NOT NULL,
    status public.placementstatus NOT NULL,
    publication_format public.publicationformat NOT NULL,
    ad_text text NOT NULL,
    proposed_price numeric(10,2) NOT NULL,
    final_price numeric(10,2),
    proposed_schedule timestamp with time zone,
    final_schedule timestamp with time zone,
    counter_offer_count integer DEFAULT 0 NOT NULL,
    counter_price numeric(10,2),
    counter_schedule timestamp with time zone,
    counter_comment text,
    rejection_reason text,
    expires_at timestamp with time zone,
    message_id bigint,
    scheduled_delete_at timestamp with time zone,
    deleted_at timestamp with time zone,
    published_at timestamp with time zone,
    published_reach integer,
    clicks_count integer DEFAULT 0 NOT NULL,
    tracking_short_code character varying(16),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    is_test boolean DEFAULT false NOT NULL,
    test_label character varying(64),
    sent_count integer DEFAULT 0 NOT NULL,
    failed_count integer DEFAULT 0 NOT NULL,
    click_count integer DEFAULT 0 NOT NULL,
    last_published_at timestamp with time zone,
    media_type character varying(10) DEFAULT 'none'::character varying NOT NULL,
    video_file_id character varying(200),
    video_url character varying(500),
    video_thumbnail_file_id character varying(200),
    video_duration integer,
    erid character varying(100),
    escrow_transaction_id integer,
    meta_json jsonb
);


--
-- Name: placement_requests_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.placement_requests_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: placement_requests_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.placement_requests_id_seq OWNED BY public.placement_requests.id;


--
-- Name: platform_account; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.platform_account (
    id integer NOT NULL,
    escrow_reserved numeric(14,2) DEFAULT '0'::numeric NOT NULL,
    payout_reserved numeric(14,2) DEFAULT '0'::numeric NOT NULL,
    profit_accumulated numeric(14,2) DEFAULT '0'::numeric NOT NULL,
    total_topups numeric(14,2) DEFAULT '0'::numeric NOT NULL,
    total_payouts numeric(14,2) DEFAULT '0'::numeric NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    legal_name character varying(500),
    inn text,
    kpp character varying(9),
    ogrn character varying(15),
    address text,
    bank_name character varying(200),
    bank_account text,
    bank_bik character varying(9),
    bank_corr_account text
);


--
-- Name: platform_account_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.platform_account_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: platform_account_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.platform_account_id_seq OWNED BY public.platform_account.id;


--
-- Name: platform_quarterly_revenues; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.platform_quarterly_revenues (
    id integer NOT NULL,
    year integer NOT NULL,
    quarter integer NOT NULL,
    usn_revenue numeric(14,2) DEFAULT '0'::numeric NOT NULL,
    vat_accumulated numeric(14,2) DEFAULT '0'::numeric NOT NULL,
    ndfl_withheld numeric(14,2) DEFAULT '0'::numeric NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    total_expenses numeric(14,2) DEFAULT '0'::numeric NOT NULL,
    tax_base_15 numeric(14,2) DEFAULT '0'::numeric NOT NULL,
    calculated_tax_15 numeric(14,2) DEFAULT '0'::numeric NOT NULL,
    min_tax_1 numeric(14,2) DEFAULT '0'::numeric NOT NULL,
    tax_due numeric(14,2) DEFAULT '0'::numeric NOT NULL,
    applicable_rate character varying(5)
);


--
-- Name: platform_quarterly_revenues_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.platform_quarterly_revenues_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: platform_quarterly_revenues_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.platform_quarterly_revenues_id_seq OWNED BY public.platform_quarterly_revenues.id;


--
-- Name: publication_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.publication_logs (
    id bigint NOT NULL,
    placement_id integer NOT NULL,
    channel_id bigint NOT NULL,
    event_type character varying(30) NOT NULL,
    message_id bigint,
    post_url character varying(500),
    erid character varying(100),
    detected_at timestamp with time zone DEFAULT now() NOT NULL,
    extra jsonb
);


--
-- Name: publication_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.publication_logs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: publication_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.publication_logs_id_seq OWNED BY public.publication_logs.id;


--
-- Name: reputation_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.reputation_history (
    id integer NOT NULL,
    user_id integer NOT NULL,
    role character varying(16) NOT NULL,
    action public.reputationaction NOT NULL,
    delta double precision NOT NULL,
    score_before double precision NOT NULL,
    score_after double precision NOT NULL,
    placement_request_id integer,
    description text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: reputation_history_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.reputation_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: reputation_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.reputation_history_id_seq OWNED BY public.reputation_history.id;


--
-- Name: reputation_scores; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.reputation_scores (
    user_id integer NOT NULL,
    advertiser_score double precision DEFAULT '5'::double precision NOT NULL,
    owner_score double precision DEFAULT '5'::double precision NOT NULL,
    is_advertiser_blocked boolean DEFAULT false NOT NULL,
    is_owner_blocked boolean DEFAULT false NOT NULL,
    advertiser_blocked_until timestamp with time zone,
    owner_blocked_until timestamp with time zone,
    advertiser_violations_count integer DEFAULT 0 NOT NULL,
    owner_violations_count integer DEFAULT 0 NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: reviews; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.reviews (
    id integer NOT NULL,
    placement_request_id integer NOT NULL,
    reviewer_id integer NOT NULL,
    reviewed_id integer NOT NULL,
    rating integer NOT NULL,
    comment text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT check_rating_range CHECK (((rating >= 1) AND (rating <= 5)))
);


--
-- Name: reviews_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.reviews_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: reviews_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.reviews_id_seq OWNED BY public.reviews.id;


--
-- Name: telegram_chats; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.telegram_chats (
    id integer NOT NULL,
    telegram_id bigint NOT NULL,
    username character varying(64) NOT NULL,
    title character varying(256) NOT NULL,
    owner_id integer NOT NULL,
    member_count integer DEFAULT 0 NOT NULL,
    last_er double precision DEFAULT '0'::double precision NOT NULL,
    avg_views integer DEFAULT 0 NOT NULL,
    rating double precision DEFAULT '0'::double precision NOT NULL,
    category character varying(32),
    description text,
    is_active boolean DEFAULT true NOT NULL,
    last_parsed_at timestamp without time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    is_test boolean DEFAULT false NOT NULL
);


--
-- Name: telegram_chats_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.telegram_chats_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: telegram_chats_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.telegram_chats_id_seq OWNED BY public.telegram_chats.id;


--
-- Name: transactions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.transactions (
    id integer NOT NULL,
    user_id integer NOT NULL,
    type public.transactiontype NOT NULL,
    amount numeric(12,2) NOT NULL,
    placement_request_id integer,
    payout_id integer,
    yookassa_payment_id character varying(64),
    description text,
    meta_json json,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    payment_status character varying(32),
    balance_before numeric(12,2),
    balance_after numeric(12,2),
    contract_id integer,
    counterparty_legal_status character varying(30),
    currency character varying(3) DEFAULT 'RUB'::character varying NOT NULL,
    vat_amount numeric(12,2) DEFAULT '0'::numeric NOT NULL,
    expense_category character varying(30),
    is_tax_deductible boolean DEFAULT false NOT NULL,
    reverses_transaction_id integer,
    is_reversed boolean DEFAULT false NOT NULL,
    act_id integer,
    invoice_id integer
);


--
-- Name: transactions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.transactions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: transactions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.transactions_id_seq OWNED BY public.transactions.id;


--
-- Name: user_badges; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_badges (
    id integer NOT NULL,
    user_id integer NOT NULL,
    badge_type character varying(64) NOT NULL,
    role character varying(16) NOT NULL,
    earned_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    badge_id integer
);


--
-- Name: user_badges_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.user_badges_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: user_badges_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.user_badges_id_seq OWNED BY public.user_badges.id;


--
-- Name: user_feedback; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_feedback (
    id integer NOT NULL,
    user_id integer NOT NULL,
    text text NOT NULL,
    status character varying(32) DEFAULT 'NEW'::character varying NOT NULL,
    admin_response text,
    responded_at timestamp with time zone,
    responded_by_id integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: user_feedback_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.user_feedback_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: user_feedback_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.user_feedback_id_seq OWNED BY public.user_feedback.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id integer NOT NULL,
    telegram_id bigint NOT NULL,
    username character varying(64),
    first_name character varying(256) NOT NULL,
    last_name character varying(256),
    is_admin boolean DEFAULT false NOT NULL,
    "current_role" character varying(16) DEFAULT 'new'::character varying NOT NULL,
    plan character varying(16) DEFAULT 'free'::character varying NOT NULL,
    plan_expires_at timestamp with time zone,
    terms_accepted_at timestamp with time zone,
    balance_rub numeric(12,2) DEFAULT '0'::numeric NOT NULL,
    earned_rub numeric(12,2) DEFAULT '0'::numeric NOT NULL,
    credits integer DEFAULT 0 NOT NULL,
    referral_code character varying(32) NOT NULL,
    referred_by_id integer,
    advertiser_xp integer DEFAULT 0 NOT NULL,
    advertiser_level integer DEFAULT 1 NOT NULL,
    owner_xp integer DEFAULT 0 NOT NULL,
    owner_level integer DEFAULT 1 NOT NULL,
    ai_uses_count integer DEFAULT 0 NOT NULL,
    ai_uses_reset_at timestamp with time zone,
    is_active boolean DEFAULT true NOT NULL,
    notifications_enabled boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    legal_status_completed boolean DEFAULT false NOT NULL,
    legal_profile_prompted_at timestamp with time zone,
    legal_profile_skipped_at timestamp with time zone,
    platform_rules_accepted_at timestamp with time zone,
    privacy_policy_accepted_at timestamp with time zone,
    login_streak_days integer DEFAULT 0 NOT NULL,
    max_streak_days integer DEFAULT 0 NOT NULL,
    language_code character varying(10)
);


--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: yookassa_payments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.yookassa_payments (
    id integer NOT NULL,
    payment_id character varying(64) NOT NULL,
    user_id integer NOT NULL,
    gross_amount numeric(12,2) NOT NULL,
    desired_balance numeric(12,2) NOT NULL,
    fee_amount numeric(12,2) NOT NULL,
    status character varying(16) DEFAULT 'pending'::character varying NOT NULL,
    payment_url text,
    processed_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    payment_method_type character varying(16),
    receipt_id character varying(64),
    yookassa_metadata jsonb
);


--
-- Name: yookassa_payments_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.yookassa_payments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: yookassa_payments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.yookassa_payments_id_seq OWNED BY public.yookassa_payments.id;


--
-- Name: acts id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.acts ALTER COLUMN id SET DEFAULT nextval('public.acts_id_seq'::regclass);


--
-- Name: audit_logs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs ALTER COLUMN id SET DEFAULT nextval('public.audit_logs_id_seq'::regclass);


--
-- Name: badge_achievements id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.badge_achievements ALTER COLUMN id SET DEFAULT nextval('public.badge_achievements_id_seq'::regclass);


--
-- Name: badges id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.badges ALTER COLUMN id SET DEFAULT nextval('public.badges_id_seq'::regclass);


--
-- Name: categories id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.categories ALTER COLUMN id SET DEFAULT nextval('public.categories_id_seq'::regclass);


--
-- Name: channel_mediakits id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.channel_mediakits ALTER COLUMN id SET DEFAULT nextval('public.channel_mediakits_id_seq'::regclass);


--
-- Name: contract_signatures id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contract_signatures ALTER COLUMN id SET DEFAULT nextval('public.contract_signatures_id_seq'::regclass);


--
-- Name: contracts id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contracts ALTER COLUMN id SET DEFAULT nextval('public.contracts_id_seq'::regclass);


--
-- Name: document_uploads id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_uploads ALTER COLUMN id SET DEFAULT nextval('public.document_uploads_id_seq'::regclass);


--
-- Name: invoices id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoices ALTER COLUMN id SET DEFAULT nextval('public.invoices_id_seq'::regclass);


--
-- Name: kudir_records id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kudir_records ALTER COLUMN id SET DEFAULT nextval('public.kudir_records_id_seq'::regclass);


--
-- Name: legal_profiles id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.legal_profiles ALTER COLUMN id SET DEFAULT nextval('public.legal_profiles_id_seq'::regclass);


--
-- Name: ord_registrations id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ord_registrations ALTER COLUMN id SET DEFAULT nextval('public.ord_registrations_id_seq'::regclass);


--
-- Name: payout_requests id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payout_requests ALTER COLUMN id SET DEFAULT nextval('public.payout_requests_id_seq'::regclass);


--
-- Name: placement_disputes id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.placement_disputes ALTER COLUMN id SET DEFAULT nextval('public.placement_disputes_id_seq'::regclass);


--
-- Name: placement_requests id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.placement_requests ALTER COLUMN id SET DEFAULT nextval('public.placement_requests_id_seq'::regclass);


--
-- Name: platform_account id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.platform_account ALTER COLUMN id SET DEFAULT nextval('public.platform_account_id_seq'::regclass);


--
-- Name: platform_quarterly_revenues id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.platform_quarterly_revenues ALTER COLUMN id SET DEFAULT nextval('public.platform_quarterly_revenues_id_seq'::regclass);


--
-- Name: publication_logs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.publication_logs ALTER COLUMN id SET DEFAULT nextval('public.publication_logs_id_seq'::regclass);


--
-- Name: reputation_history id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reputation_history ALTER COLUMN id SET DEFAULT nextval('public.reputation_history_id_seq'::regclass);


--
-- Name: reviews id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reviews ALTER COLUMN id SET DEFAULT nextval('public.reviews_id_seq'::regclass);


--
-- Name: telegram_chats id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.telegram_chats ALTER COLUMN id SET DEFAULT nextval('public.telegram_chats_id_seq'::regclass);


--
-- Name: transactions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.transactions ALTER COLUMN id SET DEFAULT nextval('public.transactions_id_seq'::regclass);


--
-- Name: user_badges id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_badges ALTER COLUMN id SET DEFAULT nextval('public.user_badges_id_seq'::regclass);


--
-- Name: user_feedback id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_feedback ALTER COLUMN id SET DEFAULT nextval('public.user_feedback_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: yookassa_payments id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.yookassa_payments ALTER COLUMN id SET DEFAULT nextval('public.yookassa_payments_id_seq'::regclass);


--
-- Name: acts acts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.acts
    ADD CONSTRAINT acts_pkey PRIMARY KEY (id);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: audit_logs audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_pkey PRIMARY KEY (id);


--
-- Name: badge_achievements badge_achievements_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.badge_achievements
    ADD CONSTRAINT badge_achievements_pkey PRIMARY KEY (id);


--
-- Name: badges badges_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.badges
    ADD CONSTRAINT badges_code_key UNIQUE (code);


--
-- Name: badges badges_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.badges
    ADD CONSTRAINT badges_pkey PRIMARY KEY (id);


--
-- Name: categories categories_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.categories
    ADD CONSTRAINT categories_pkey PRIMARY KEY (id);


--
-- Name: channel_mediakits channel_mediakits_channel_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.channel_mediakits
    ADD CONSTRAINT channel_mediakits_channel_id_key UNIQUE (channel_id);


--
-- Name: channel_mediakits channel_mediakits_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.channel_mediakits
    ADD CONSTRAINT channel_mediakits_pkey PRIMARY KEY (id);


--
-- Name: channel_settings channel_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.channel_settings
    ADD CONSTRAINT channel_settings_pkey PRIMARY KEY (channel_id);


--
-- Name: contract_signatures contract_signatures_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contract_signatures
    ADD CONSTRAINT contract_signatures_pkey PRIMARY KEY (id);


--
-- Name: contracts contracts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contracts
    ADD CONSTRAINT contracts_pkey PRIMARY KEY (id);


--
-- Name: document_counters document_counters_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_counters
    ADD CONSTRAINT document_counters_pkey PRIMARY KEY (prefix, year);


--
-- Name: document_uploads document_uploads_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_uploads
    ADD CONSTRAINT document_uploads_pkey PRIMARY KEY (id);


--
-- Name: invoices invoices_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT invoices_pkey PRIMARY KEY (id);


--
-- Name: kudir_records kudir_records_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kudir_records
    ADD CONSTRAINT kudir_records_pkey PRIMARY KEY (id);


--
-- Name: legal_profiles legal_profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.legal_profiles
    ADD CONSTRAINT legal_profiles_pkey PRIMARY KEY (id);


--
-- Name: legal_profiles legal_profiles_user_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.legal_profiles
    ADD CONSTRAINT legal_profiles_user_id_key UNIQUE (user_id);


--
-- Name: ord_registrations ord_registrations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ord_registrations
    ADD CONSTRAINT ord_registrations_pkey PRIMARY KEY (id);


--
-- Name: ord_registrations ord_registrations_placement_request_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ord_registrations
    ADD CONSTRAINT ord_registrations_placement_request_id_key UNIQUE (placement_request_id);


--
-- Name: payout_requests payout_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payout_requests
    ADD CONSTRAINT payout_requests_pkey PRIMARY KEY (id);


--
-- Name: placement_disputes placement_disputes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.placement_disputes
    ADD CONSTRAINT placement_disputes_pkey PRIMARY KEY (id);


--
-- Name: placement_requests placement_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.placement_requests
    ADD CONSTRAINT placement_requests_pkey PRIMARY KEY (id);


--
-- Name: placement_requests placement_requests_tracking_short_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.placement_requests
    ADD CONSTRAINT placement_requests_tracking_short_code_key UNIQUE (tracking_short_code);


--
-- Name: platform_account platform_account_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.platform_account
    ADD CONSTRAINT platform_account_pkey PRIMARY KEY (id);


--
-- Name: platform_quarterly_revenues platform_quarterly_revenues_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.platform_quarterly_revenues
    ADD CONSTRAINT platform_quarterly_revenues_pkey PRIMARY KEY (id);


--
-- Name: publication_logs publication_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.publication_logs
    ADD CONSTRAINT publication_logs_pkey PRIMARY KEY (id);


--
-- Name: reputation_history reputation_history_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reputation_history
    ADD CONSTRAINT reputation_history_pkey PRIMARY KEY (id);


--
-- Name: reputation_scores reputation_scores_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reputation_scores
    ADD CONSTRAINT reputation_scores_pkey PRIMARY KEY (user_id);


--
-- Name: reviews reviews_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_pkey PRIMARY KEY (id);


--
-- Name: telegram_chats telegram_chats_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.telegram_chats
    ADD CONSTRAINT telegram_chats_pkey PRIMARY KEY (id);


--
-- Name: telegram_chats telegram_chats_username_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.telegram_chats
    ADD CONSTRAINT telegram_chats_username_key UNIQUE (username);


--
-- Name: transactions transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_pkey PRIMARY KEY (id);


--
-- Name: mailing_logs uq_mailing_placement_chat; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mailing_logs
    ADD CONSTRAINT uq_mailing_placement_chat UNIQUE (placement_request_id, chat_id);


--
-- Name: platform_quarterly_revenues uq_platform_quarterly_revenues_year_quarter; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.platform_quarterly_revenues
    ADD CONSTRAINT uq_platform_quarterly_revenues_year_quarter UNIQUE (year, quarter);


--
-- Name: reviews uq_reviews_placement_reviewer; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT uq_reviews_placement_reviewer UNIQUE (placement_request_id, reviewer_id);


--
-- Name: user_badges user_badges_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_badges
    ADD CONSTRAINT user_badges_pkey PRIMARY KEY (id);


--
-- Name: user_feedback user_feedback_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_feedback
    ADD CONSTRAINT user_feedback_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: users users_referral_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_referral_code_key UNIQUE (referral_code);


--
-- Name: yookassa_payments yookassa_payments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.yookassa_payments
    ADD CONSTRAINT yookassa_payments_pkey PRIMARY KEY (id);


--
-- Name: ix_acts_act_number; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_acts_act_number ON public.acts USING btree (act_number);


--
-- Name: ix_acts_contract_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_acts_contract_id ON public.acts USING btree (contract_id);


--
-- Name: ix_acts_placement_request_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_acts_placement_request_id ON public.acts USING btree (placement_request_id);


--
-- Name: ix_acts_sign_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_acts_sign_status ON public.acts USING btree (sign_status);


--
-- Name: ix_audit_logs_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_logs_created_at ON public.audit_logs USING btree (created_at);


--
-- Name: ix_audit_logs_resource; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_logs_resource ON public.audit_logs USING btree (resource_type, resource_id);


--
-- Name: ix_audit_logs_target_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_logs_target_user_id ON public.audit_logs USING btree (target_user_id);


--
-- Name: ix_audit_logs_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_logs_user_id ON public.audit_logs USING btree (user_id);


--
-- Name: ix_categories_slug; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_categories_slug ON public.categories USING btree (slug);


--
-- Name: ix_click_tracking_placement_request_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_click_tracking_placement_request_id ON public.click_tracking USING btree (placement_request_id);


--
-- Name: ix_click_tracking_short_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_click_tracking_short_code ON public.click_tracking USING btree (short_code);


--
-- Name: ix_contract_signatures_contract_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_contract_signatures_contract_id ON public.contract_signatures USING btree (contract_id);


--
-- Name: ix_contract_signatures_signed_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_contract_signatures_signed_at ON public.contract_signatures USING btree (signed_at);


--
-- Name: ix_contract_signatures_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_contract_signatures_user_id ON public.contract_signatures USING btree (user_id);


--
-- Name: ix_contracts_placement_request_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_contracts_placement_request_id ON public.contracts USING btree (placement_request_id);


--
-- Name: ix_contracts_type_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_contracts_type_status ON public.contracts USING btree (contract_type, contract_status);


--
-- Name: ix_contracts_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_contracts_user_id ON public.contracts USING btree (user_id);


--
-- Name: ix_document_uploads_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_document_uploads_user_id ON public.document_uploads USING btree (user_id);


--
-- Name: ix_invoices_contract_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_invoices_contract_id ON public.invoices USING btree (contract_id);


--
-- Name: ix_invoices_invoice_number; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_invoices_invoice_number ON public.invoices USING btree (invoice_number);


--
-- Name: ix_invoices_placement_request_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_invoices_placement_request_id ON public.invoices USING btree (placement_request_id);


--
-- Name: ix_invoices_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_invoices_user_id ON public.invoices USING btree (user_id);


--
-- Name: ix_kudir_records_operation_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_kudir_records_operation_type ON public.kudir_records USING btree (operation_type);


--
-- Name: ix_kudir_records_quarter_entry; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_kudir_records_quarter_entry ON public.kudir_records USING btree (quarter, entry_number);


--
-- Name: ix_legal_profiles_inn_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_legal_profiles_inn_hash ON public.legal_profiles USING btree (inn_hash);


--
-- Name: ix_legal_profiles_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_legal_profiles_user_id ON public.legal_profiles USING btree (user_id);


--
-- Name: ix_mailing_logs_campaign_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_mailing_logs_campaign_id ON public.mailing_logs USING btree (campaign_id);


--
-- Name: ix_mailing_logs_chat_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_mailing_logs_chat_id ON public.mailing_logs USING btree (chat_id);


--
-- Name: ix_mailing_logs_chat_telegram_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_mailing_logs_chat_telegram_id ON public.mailing_logs USING btree (chat_telegram_id);


--
-- Name: ix_mailing_logs_placement_request_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_mailing_logs_placement_request_id ON public.mailing_logs USING btree (placement_request_id);


--
-- Name: ix_mailing_logs_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_mailing_logs_status ON public.mailing_logs USING btree (status);


--
-- Name: ix_mailing_sent_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_mailing_sent_at ON public.mailing_logs USING btree (sent_at);


--
-- Name: ix_mailing_status_chat; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_mailing_status_chat ON public.mailing_logs USING btree (status, chat_id);


--
-- Name: ix_ord_registrations_erid; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ord_registrations_erid ON public.ord_registrations USING btree (erid);


--
-- Name: ix_ord_registrations_placement_request_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_ord_registrations_placement_request_id ON public.ord_registrations USING btree (placement_request_id);


--
-- Name: ix_payout_requests_owner_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_payout_requests_owner_id ON public.payout_requests USING btree (owner_id);


--
-- Name: ix_payout_requests_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_payout_requests_status ON public.payout_requests USING btree (status);


--
-- Name: ix_placement_disputes_placement_request_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_placement_disputes_placement_request_id ON public.placement_disputes USING btree (placement_request_id);


--
-- Name: ix_placement_disputes_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_placement_disputes_status ON public.placement_disputes USING btree (status);


--
-- Name: ix_placement_requests_advertiser_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_placement_requests_advertiser_id ON public.placement_requests USING btree (advertiser_id);


--
-- Name: ix_placement_requests_channel_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_placement_requests_channel_id ON public.placement_requests USING btree (channel_id);


--
-- Name: ix_placement_requests_escrow_transaction_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_placement_requests_escrow_transaction_id ON public.placement_requests USING btree (escrow_transaction_id);


--
-- Name: ix_placement_requests_expires_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_placement_requests_expires_at ON public.placement_requests USING btree (expires_at);


--
-- Name: ix_placement_requests_is_test; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_placement_requests_is_test ON public.placement_requests USING btree (is_test);


--
-- Name: ix_placement_requests_owner_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_placement_requests_owner_id ON public.placement_requests USING btree (owner_id);


--
-- Name: ix_placement_requests_scheduled_delete_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_placement_requests_scheduled_delete_at ON public.placement_requests USING btree (scheduled_delete_at);


--
-- Name: ix_placement_requests_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_placement_requests_status ON public.placement_requests USING btree (status);


--
-- Name: ix_placement_requests_status_expires; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_placement_requests_status_expires ON public.placement_requests USING btree (status, expires_at);


--
-- Name: ix_publication_logs_channel_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_publication_logs_channel_id ON public.publication_logs USING btree (channel_id);


--
-- Name: ix_publication_logs_detected_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_publication_logs_detected_at ON public.publication_logs USING btree (detected_at);


--
-- Name: ix_publication_logs_event_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_publication_logs_event_type ON public.publication_logs USING btree (event_type);


--
-- Name: ix_publication_logs_placement_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_publication_logs_placement_id ON public.publication_logs USING btree (placement_id);


--
-- Name: ix_reputation_history_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_reputation_history_user_id ON public.reputation_history USING btree (user_id);


--
-- Name: ix_reviews_reviewed_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_reviews_reviewed_id ON public.reviews USING btree (reviewed_id);


--
-- Name: ix_reviews_reviewer_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_reviews_reviewer_id ON public.reviews USING btree (reviewer_id);


--
-- Name: ix_telegram_chats_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_telegram_chats_category ON public.telegram_chats USING btree (category);


--
-- Name: ix_telegram_chats_is_test; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_telegram_chats_is_test ON public.telegram_chats USING btree (is_test);


--
-- Name: ix_telegram_chats_owner_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_telegram_chats_owner_id ON public.telegram_chats USING btree (owner_id);


--
-- Name: ix_telegram_chats_telegram_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_telegram_chats_telegram_id ON public.telegram_chats USING btree (telegram_id);


--
-- Name: ix_transactions_contract_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_transactions_contract_id ON public.transactions USING btree (contract_id);


--
-- Name: ix_transactions_placement_request_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_transactions_placement_request_id ON public.transactions USING btree (placement_request_id);


--
-- Name: ix_transactions_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_transactions_type ON public.transactions USING btree (type);


--
-- Name: ix_transactions_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_transactions_user_id ON public.transactions USING btree (user_id);


--
-- Name: ix_txn_act_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_txn_act_id ON public.transactions USING btree (act_id);


--
-- Name: ix_txn_invoice_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_txn_invoice_id ON public.transactions USING btree (invoice_id);


--
-- Name: ix_txn_reverses_transaction_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_txn_reverses_transaction_id ON public.transactions USING btree (reverses_transaction_id);


--
-- Name: ix_user_badges_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_user_badges_user_id ON public.user_badges USING btree (user_id);


--
-- Name: ix_user_feedback_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_user_feedback_status ON public.user_feedback USING btree (status);


--
-- Name: ix_user_feedback_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_user_feedback_user_id ON public.user_feedback USING btree (user_id);


--
-- Name: ix_users_telegram_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_users_telegram_id ON public.users USING btree (telegram_id);


--
-- Name: ix_yookassa_payments_payment_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_yookassa_payments_payment_id ON public.yookassa_payments USING btree (payment_id);


--
-- Name: ix_yookassa_payments_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_yookassa_payments_user_id ON public.yookassa_payments USING btree (user_id);


--
-- Name: acts acts_placement_request_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.acts
    ADD CONSTRAINT acts_placement_request_id_fkey FOREIGN KEY (placement_request_id) REFERENCES public.placement_requests(id);


--
-- Name: badge_achievements badge_achievements_badge_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.badge_achievements
    ADD CONSTRAINT badge_achievements_badge_id_fkey FOREIGN KEY (badge_id) REFERENCES public.badges(id);


--
-- Name: channel_mediakits channel_mediakits_channel_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.channel_mediakits
    ADD CONSTRAINT channel_mediakits_channel_id_fkey FOREIGN KEY (channel_id) REFERENCES public.telegram_chats(id);


--
-- Name: channel_settings channel_settings_channel_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.channel_settings
    ADD CONSTRAINT channel_settings_channel_id_fkey FOREIGN KEY (channel_id) REFERENCES public.telegram_chats(id);


--
-- Name: click_tracking click_tracking_placement_request_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.click_tracking
    ADD CONSTRAINT click_tracking_placement_request_id_fkey FOREIGN KEY (placement_request_id) REFERENCES public.placement_requests(id) ON DELETE CASCADE;


--
-- Name: contract_signatures contract_signatures_contract_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contract_signatures
    ADD CONSTRAINT contract_signatures_contract_id_fkey FOREIGN KEY (contract_id) REFERENCES public.contracts(id);


--
-- Name: contract_signatures contract_signatures_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contract_signatures
    ADD CONSTRAINT contract_signatures_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: contracts contracts_placement_request_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contracts
    ADD CONSTRAINT contracts_placement_request_id_fkey FOREIGN KEY (placement_request_id) REFERENCES public.placement_requests(id);


--
-- Name: contracts contracts_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contracts
    ADD CONSTRAINT contracts_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: acts fk_acts_contract_id_contracts; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.acts
    ADD CONSTRAINT fk_acts_contract_id_contracts FOREIGN KEY (contract_id) REFERENCES public.contracts(id) ON DELETE SET NULL;


--
-- Name: invoices fk_invoices_contract_id_contracts; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT fk_invoices_contract_id_contracts FOREIGN KEY (contract_id) REFERENCES public.contracts(id) ON DELETE SET NULL;


--
-- Name: invoices fk_invoices_placement_request_id_placement_requests; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT fk_invoices_placement_request_id_placement_requests FOREIGN KEY (placement_request_id) REFERENCES public.placement_requests(id) ON DELETE SET NULL;


--
-- Name: invoices fk_invoices_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT fk_invoices_user_id FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: transactions fk_transactions_contract_id_contracts; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT fk_transactions_contract_id_contracts FOREIGN KEY (contract_id) REFERENCES public.contracts(id);


--
-- Name: transactions fk_txn_act_id_acts; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT fk_txn_act_id_acts FOREIGN KEY (act_id) REFERENCES public.acts(id) ON DELETE SET NULL;


--
-- Name: transactions fk_txn_invoice_id_invoices; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT fk_txn_invoice_id_invoices FOREIGN KEY (invoice_id) REFERENCES public.invoices(id) ON DELETE SET NULL;


--
-- Name: transactions fk_txn_reverses; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT fk_txn_reverses FOREIGN KEY (reverses_transaction_id) REFERENCES public.transactions(id);


--
-- Name: user_badges fk_user_badges_badge_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_badges
    ADD CONSTRAINT fk_user_badges_badge_id FOREIGN KEY (badge_id) REFERENCES public.badges(id);


--
-- Name: legal_profiles legal_profiles_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.legal_profiles
    ADD CONSTRAINT legal_profiles_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: mailing_logs mailing_logs_chat_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mailing_logs
    ADD CONSTRAINT mailing_logs_chat_id_fkey FOREIGN KEY (chat_id) REFERENCES public.telegram_chats(id) ON DELETE SET NULL;


--
-- Name: mailing_logs mailing_logs_placement_request_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mailing_logs
    ADD CONSTRAINT mailing_logs_placement_request_id_fkey FOREIGN KEY (placement_request_id) REFERENCES public.placement_requests(id) ON DELETE SET NULL;


--
-- Name: ord_registrations ord_registrations_contract_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ord_registrations
    ADD CONSTRAINT ord_registrations_contract_id_fkey FOREIGN KEY (contract_id) REFERENCES public.contracts(id);


--
-- Name: ord_registrations ord_registrations_placement_request_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ord_registrations
    ADD CONSTRAINT ord_registrations_placement_request_id_fkey FOREIGN KEY (placement_request_id) REFERENCES public.placement_requests(id);


--
-- Name: payout_requests payout_requests_admin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payout_requests
    ADD CONSTRAINT payout_requests_admin_id_fkey FOREIGN KEY (admin_id) REFERENCES public.users(id);


--
-- Name: payout_requests payout_requests_owner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payout_requests
    ADD CONSTRAINT payout_requests_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES public.users(id);


--
-- Name: placement_disputes placement_disputes_admin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.placement_disputes
    ADD CONSTRAINT placement_disputes_admin_id_fkey FOREIGN KEY (admin_id) REFERENCES public.users(id);


--
-- Name: placement_disputes placement_disputes_advertiser_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.placement_disputes
    ADD CONSTRAINT placement_disputes_advertiser_id_fkey FOREIGN KEY (advertiser_id) REFERENCES public.users(id);


--
-- Name: placement_disputes placement_disputes_owner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.placement_disputes
    ADD CONSTRAINT placement_disputes_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES public.users(id);


--
-- Name: placement_disputes placement_disputes_placement_request_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.placement_disputes
    ADD CONSTRAINT placement_disputes_placement_request_id_fkey FOREIGN KEY (placement_request_id) REFERENCES public.placement_requests(id);


--
-- Name: placement_requests placement_requests_advertiser_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.placement_requests
    ADD CONSTRAINT placement_requests_advertiser_id_fkey FOREIGN KEY (advertiser_id) REFERENCES public.users(id);


--
-- Name: placement_requests placement_requests_channel_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.placement_requests
    ADD CONSTRAINT placement_requests_channel_id_fkey FOREIGN KEY (channel_id) REFERENCES public.telegram_chats(id);


--
-- Name: placement_requests placement_requests_escrow_transaction_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.placement_requests
    ADD CONSTRAINT placement_requests_escrow_transaction_id_fkey FOREIGN KEY (escrow_transaction_id) REFERENCES public.transactions(id);


--
-- Name: placement_requests placement_requests_owner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.placement_requests
    ADD CONSTRAINT placement_requests_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES public.users(id);


--
-- Name: publication_logs publication_logs_placement_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.publication_logs
    ADD CONSTRAINT publication_logs_placement_id_fkey FOREIGN KEY (placement_id) REFERENCES public.placement_requests(id) ON DELETE RESTRICT;


--
-- Name: reputation_history reputation_history_placement_request_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reputation_history
    ADD CONSTRAINT reputation_history_placement_request_id_fkey FOREIGN KEY (placement_request_id) REFERENCES public.placement_requests(id);


--
-- Name: reputation_history reputation_history_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reputation_history
    ADD CONSTRAINT reputation_history_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: reputation_scores reputation_scores_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reputation_scores
    ADD CONSTRAINT reputation_scores_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: reviews reviews_placement_request_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_placement_request_id_fkey FOREIGN KEY (placement_request_id) REFERENCES public.placement_requests(id);


--
-- Name: reviews reviews_reviewed_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_reviewed_id_fkey FOREIGN KEY (reviewed_id) REFERENCES public.users(id);


--
-- Name: reviews reviews_reviewer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_reviewer_id_fkey FOREIGN KEY (reviewer_id) REFERENCES public.users(id);


--
-- Name: telegram_chats telegram_chats_owner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.telegram_chats
    ADD CONSTRAINT telegram_chats_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES public.users(id);


--
-- Name: transactions transactions_payout_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_payout_id_fkey FOREIGN KEY (payout_id) REFERENCES public.payout_requests(id);


--
-- Name: transactions transactions_placement_request_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_placement_request_id_fkey FOREIGN KEY (placement_request_id) REFERENCES public.placement_requests(id);


--
-- Name: transactions transactions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: user_badges user_badges_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_badges
    ADD CONSTRAINT user_badges_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: user_feedback user_feedback_responded_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_feedback
    ADD CONSTRAINT user_feedback_responded_by_id_fkey FOREIGN KEY (responded_by_id) REFERENCES public.users(id);


--
-- Name: user_feedback user_feedback_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_feedback
    ADD CONSTRAINT user_feedback_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: users users_referred_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_referred_by_id_fkey FOREIGN KEY (referred_by_id) REFERENCES public.users(id);


--
-- Name: yookassa_payments yookassa_payments_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.yookassa_payments
    ADD CONSTRAINT yookassa_payments_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- PostgreSQL database dump complete
--

\unrestrict KbqBct9beXuPBp0JjxRPbSKlZPHLoky50afas5aSt9v7vVwa7uMnQJdM4LekvCN

