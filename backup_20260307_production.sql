--
-- PostgreSQL database dump
--

\restrict b61R6y8cHfqnyj1s55qNqGUCEV6pS11jqZYSi5IOtgCJIYcJfMa0KEqTEs2Xnef

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
-- Name: public; Type: SCHEMA; Schema: -; Owner: market_bot
--

-- *not* creating schema, since initdb creates it


ALTER SCHEMA public OWNER TO market_bot;

--
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: market_bot
--

COMMENT ON SCHEMA public IS '';


--
-- Name: chattype; Type: TYPE; Schema: public; Owner: market_bot
--

CREATE TYPE public.chattype AS ENUM (
    'channel',
    'group',
    'supergroup'
);


ALTER TYPE public.chattype OWNER TO market_bot;

--
-- Name: mailingstatus; Type: TYPE; Schema: public; Owner: market_bot
--

CREATE TYPE public.mailingstatus AS ENUM (
    'sent',
    'failed',
    'skipped',
    'pending',
    'pending_approval',
    'rejected',
    'queued'
);


ALTER TYPE public.mailingstatus OWNER TO market_bot;

--
-- Name: paymentmethod; Type: TYPE; Schema: public; Owner: market_bot
--

CREATE TYPE public.paymentmethod AS ENUM (
    'cryptobot',
    'stars'
);


ALTER TYPE public.paymentmethod OWNER TO market_bot;

--
-- Name: paymentstatus; Type: TYPE; Schema: public; Owner: market_bot
--

CREATE TYPE public.paymentstatus AS ENUM (
    'pending',
    'paid',
    'expired',
    'cancelled'
);


ALTER TYPE public.paymentstatus OWNER TO market_bot;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: market_bot
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO market_bot;

--
-- Name: b2b_packages; Type: TABLE; Schema: public; Owner: market_bot
--

CREATE TABLE public.b2b_packages (
    id integer NOT NULL,
    name character varying(200) NOT NULL,
    niche character varying(30) NOT NULL,
    description text NOT NULL,
    channels_count integer NOT NULL,
    guaranteed_reach integer NOT NULL,
    min_er double precision NOT NULL,
    price numeric(12,2) NOT NULL,
    discount_pct integer NOT NULL,
    is_active boolean NOT NULL,
    channel_ids json NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.b2b_packages OWNER TO market_bot;

--
-- Name: b2b_packages_id_seq; Type: SEQUENCE; Schema: public; Owner: market_bot
--

CREATE SEQUENCE public.b2b_packages_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.b2b_packages_id_seq OWNER TO market_bot;

--
-- Name: b2b_packages_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: market_bot
--

ALTER SEQUENCE public.b2b_packages_id_seq OWNED BY public.b2b_packages.id;


--
-- Name: badges; Type: TABLE; Schema: public; Owner: market_bot
--

CREATE TABLE public.badges (
    id integer NOT NULL,
    code character varying(100) NOT NULL,
    name character varying(200) NOT NULL,
    description text NOT NULL,
    icon_emoji character varying(10) NOT NULL,
    xp_reward integer NOT NULL,
    category character varying(20) NOT NULL,
    condition_type character varying(30) NOT NULL,
    condition_value integer NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.badges OWNER TO market_bot;

--
-- Name: badges_id_seq; Type: SEQUENCE; Schema: public; Owner: market_bot
--

CREATE SEQUENCE public.badges_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.badges_id_seq OWNER TO market_bot;

--
-- Name: badges_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: market_bot
--

ALTER SEQUENCE public.badges_id_seq OWNED BY public.badges.id;


--
-- Name: campaigns; Type: TABLE; Schema: public; Owner: market_bot
--

CREATE TABLE public.campaigns (
    id integer NOT NULL,
    user_id integer NOT NULL,
    title character varying(255) NOT NULL,
    text text NOT NULL,
    ai_description text,
    status character varying(50) NOT NULL,
    filters_json jsonb,
    scheduled_at timestamp with time zone,
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    error_message text,
    total_chats integer NOT NULL,
    sent_count integer NOT NULL,
    failed_count integer NOT NULL,
    skipped_count integer NOT NULL,
    cost double precision NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    topic character varying(100),
    header character varying(255),
    image_file_id character varying(255),
    tracking_url character varying(2048),
    tracking_short_code character varying(20),
    clicks_count integer DEFAULT 0 NOT NULL
);


ALTER TABLE public.campaigns OWNER TO market_bot;

--
-- Name: TABLE campaigns; Type: COMMENT; Schema: public; Owner: market_bot
--

COMMENT ON TABLE public.campaigns IS 'Рекламные кампании пользователей';


--
-- Name: campaigns_id_seq; Type: SEQUENCE; Schema: public; Owner: market_bot
--

CREATE SEQUENCE public.campaigns_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.campaigns_id_seq OWNER TO market_bot;

--
-- Name: campaigns_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: market_bot
--

ALTER SEQUENCE public.campaigns_id_seq OWNED BY public.campaigns.id;


--
-- Name: channel_ratings; Type: TABLE; Schema: public; Owner: market_bot
--

CREATE TABLE public.channel_ratings (
    id integer NOT NULL,
    channel_id bigint NOT NULL,
    date date NOT NULL,
    subscribers integer NOT NULL,
    avg_views integer NOT NULL,
    er double precision NOT NULL,
    reach_score double precision NOT NULL,
    er_score double precision NOT NULL,
    growth_score double precision NOT NULL,
    frequency_score double precision NOT NULL,
    reliability_score double precision NOT NULL,
    age_score double precision NOT NULL,
    total_score double precision NOT NULL,
    rank_in_topic integer,
    fraud_flag boolean NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.channel_ratings OWNER TO market_bot;

--
-- Name: channel_ratings_id_seq; Type: SEQUENCE; Schema: public; Owner: market_bot
--

CREATE SEQUENCE public.channel_ratings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.channel_ratings_id_seq OWNER TO market_bot;

--
-- Name: channel_ratings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: market_bot
--

ALTER SEQUENCE public.channel_ratings_id_seq OWNED BY public.channel_ratings.id;


--
-- Name: chat_snapshots; Type: TABLE; Schema: public; Owner: market_bot
--

CREATE TABLE public.chat_snapshots (
    id integer NOT NULL,
    chat_id integer NOT NULL,
    snapshot_date date NOT NULL,
    subscribers integer NOT NULL,
    subscribers_delta integer NOT NULL,
    subscribers_delta_pct double precision NOT NULL,
    avg_views integer NOT NULL,
    max_views integer NOT NULL,
    min_views integer NOT NULL,
    posts_analyzed integer NOT NULL,
    er double precision NOT NULL,
    post_frequency double precision NOT NULL,
    posts_last_30d integer NOT NULL,
    can_post boolean NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.chat_snapshots OWNER TO market_bot;

--
-- Name: TABLE chat_snapshots; Type: COMMENT; Schema: public; Owner: market_bot
--

COMMENT ON TABLE public.chat_snapshots IS 'Ежедневные снимки метрик Telegram чатов';


--
-- Name: chat_snapshots_id_seq; Type: SEQUENCE; Schema: public; Owner: market_bot
--

CREATE SEQUENCE public.chat_snapshots_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.chat_snapshots_id_seq OWNER TO market_bot;

--
-- Name: chat_snapshots_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: market_bot
--

ALTER SEQUENCE public.chat_snapshots_id_seq OWNED BY public.chat_snapshots.id;


--
-- Name: content_flags; Type: TABLE; Schema: public; Owner: market_bot
--

CREATE TABLE public.content_flags (
    id integer NOT NULL,
    campaign_id integer NOT NULL,
    categories character varying(50)[] NOT NULL,
    flagged_fragments jsonb,
    decision character varying(50) NOT NULL,
    reviewed_by_id integer,
    review_comment text,
    filter_score double precision NOT NULL,
    llm_analysis text,
    llm_categories character varying(50)[],
    auto_checked boolean NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.content_flags OWNER TO market_bot;

--
-- Name: TABLE content_flags; Type: COMMENT; Schema: public; Owner: market_bot
--

COMMENT ON TABLE public.content_flags IS 'Флаги модерации контента';


--
-- Name: content_flags_id_seq; Type: SEQUENCE; Schema: public; Owner: market_bot
--

CREATE SEQUENCE public.content_flags_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.content_flags_id_seq OWNER TO market_bot;

--
-- Name: content_flags_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: market_bot
--

ALTER SEQUENCE public.content_flags_id_seq OWNED BY public.content_flags.id;


--
-- Name: crypto_payments; Type: TABLE; Schema: public; Owner: market_bot
--

CREATE TABLE public.crypto_payments (
    id integer NOT NULL,
    user_id integer NOT NULL,
    method public.paymentmethod NOT NULL,
    invoice_id character varying(64),
    currency character varying(16),
    amount numeric(20,8),
    telegram_payment_charge_id character varying(128),
    stars_amount integer,
    credits integer NOT NULL,
    bonus_credits integer NOT NULL,
    status public.paymentstatus NOT NULL,
    payload jsonb,
    meta_json jsonb,
    credited_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    pay_url character varying(512)
);


ALTER TABLE public.crypto_payments OWNER TO market_bot;

--
-- Name: TABLE crypto_payments; Type: COMMENT; Schema: public; Owner: market_bot
--

COMMENT ON TABLE public.crypto_payments IS 'Крипто-платежи (CryptoBot / Telegram Stars)';


--
-- Name: crypto_payments_id_seq; Type: SEQUENCE; Schema: public; Owner: market_bot
--

CREATE SEQUENCE public.crypto_payments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.crypto_payments_id_seq OWNER TO market_bot;

--
-- Name: crypto_payments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: market_bot
--

ALTER SEQUENCE public.crypto_payments_id_seq OWNED BY public.crypto_payments.id;


--
-- Name: mailing_logs; Type: TABLE; Schema: public; Owner: market_bot
--

CREATE TABLE public.mailing_logs (
    id integer NOT NULL,
    campaign_id integer NOT NULL,
    chat_id integer,
    chat_telegram_id bigint NOT NULL,
    status character varying(50) NOT NULL,
    error_msg text,
    message_id integer,
    retry_count integer NOT NULL,
    sent_at timestamp without time zone,
    cost double precision NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.mailing_logs OWNER TO market_bot;

--
-- Name: TABLE mailing_logs; Type: COMMENT; Schema: public; Owner: market_bot
--

COMMENT ON TABLE public.mailing_logs IS 'Логи рассылок по кампаниям';


--
-- Name: mailing_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: market_bot
--

CREATE SEQUENCE public.mailing_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.mailing_logs_id_seq OWNER TO market_bot;

--
-- Name: mailing_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: market_bot
--

ALTER SEQUENCE public.mailing_logs_id_seq OWNED BY public.mailing_logs.id;


--
-- Name: notifications; Type: TABLE; Schema: public; Owner: market_bot
--

CREATE TABLE public.notifications (
    id integer NOT NULL,
    user_id integer NOT NULL,
    notification_type character varying(50) NOT NULL,
    title character varying(255),
    message text NOT NULL,
    is_read boolean NOT NULL,
    campaign_id integer,
    transaction_id integer,
    error_code character varying(100),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.notifications OWNER TO market_bot;

--
-- Name: TABLE notifications; Type: COMMENT; Schema: public; Owner: market_bot
--

COMMENT ON TABLE public.notifications IS 'История уведомлений пользователей';


--
-- Name: notifications_id_seq; Type: SEQUENCE; Schema: public; Owner: market_bot
--

CREATE SEQUENCE public.notifications_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.notifications_id_seq OWNER TO market_bot;

--
-- Name: notifications_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: market_bot
--

ALTER SEQUENCE public.notifications_id_seq OWNED BY public.notifications.id;


--
-- Name: payouts; Type: TABLE; Schema: public; Owner: market_bot
--

CREATE TABLE public.payouts (
    id integer NOT NULL,
    owner_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    placement_id integer NOT NULL,
    amount numeric(10,2) NOT NULL,
    platform_fee numeric(10,2) NOT NULL,
    currency character varying(10) NOT NULL,
    status character varying(20) NOT NULL,
    wallet_address character varying(200),
    tx_hash character varying(200),
    paid_at timestamp with time zone,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.payouts OWNER TO market_bot;

--
-- Name: payouts_id_seq; Type: SEQUENCE; Schema: public; Owner: market_bot
--

CREATE SEQUENCE public.payouts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.payouts_id_seq OWNER TO market_bot;

--
-- Name: payouts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: market_bot
--

ALTER SEQUENCE public.payouts_id_seq OWNED BY public.payouts.id;


--
-- Name: reviews; Type: TABLE; Schema: public; Owner: market_bot
--

CREATE TABLE public.reviews (
    id integer NOT NULL,
    reviewer_id bigint NOT NULL,
    reviewee_id bigint NOT NULL,
    channel_id bigint,
    placement_id integer NOT NULL,
    reviewer_role character varying(20) NOT NULL,
    score_compliance integer,
    score_audience integer,
    score_speed integer,
    score_material integer,
    score_requirements integer,
    score_payment integer,
    comment text,
    is_hidden boolean NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.reviews OWNER TO market_bot;

--
-- Name: reviews_id_seq; Type: SEQUENCE; Schema: public; Owner: market_bot
--

CREATE SEQUENCE public.reviews_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.reviews_id_seq OWNER TO market_bot;

--
-- Name: reviews_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: market_bot
--

ALTER SEQUENCE public.reviews_id_seq OWNED BY public.reviews.id;


--
-- Name: telegram_chats; Type: TABLE; Schema: public; Owner: market_bot
--

CREATE TABLE public.telegram_chats (
    id integer NOT NULL,
    username character varying(255) NOT NULL,
    telegram_id bigint,
    title character varying(512),
    description text,
    chat_type public.chattype NOT NULL,
    topic character varying(100),
    is_active boolean NOT NULL,
    is_public boolean NOT NULL,
    can_post boolean NOT NULL,
    member_count integer NOT NULL,
    rating double precision NOT NULL,
    is_scam boolean NOT NULL,
    is_fake boolean NOT NULL,
    error_count integer NOT NULL,
    deactivate_reason character varying(500),
    last_subscribers integer NOT NULL,
    last_avg_views integer NOT NULL,
    last_er double precision NOT NULL,
    last_post_frequency double precision NOT NULL,
    last_parsed_at timestamp without time zone,
    parse_error text,
    parse_error_count integer NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    subcategory character varying(50),
    language character varying(10) NOT NULL,
    russian_score double precision NOT NULL,
    complaint_count integer NOT NULL,
    last_complaint_at timestamp with time zone,
    is_blacklisted boolean NOT NULL,
    blacklisted_reason character varying(500),
    blacklisted_at timestamp with time zone,
    consecutive_failures integer NOT NULL,
    last_classified_at timestamp with time zone,
    llm_confidence double precision,
    recent_posts json,
    bot_is_admin boolean DEFAULT false NOT NULL,
    admin_added_at timestamp with time zone,
    owner_user_id bigint,
    price_per_post numeric(10,2),
    is_accepting_ads boolean DEFAULT false NOT NULL
);


ALTER TABLE public.telegram_chats OWNER TO market_bot;

--
-- Name: telegram_chats_id_seq; Type: SEQUENCE; Schema: public; Owner: market_bot
--

CREATE SEQUENCE public.telegram_chats_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.telegram_chats_id_seq OWNER TO market_bot;

--
-- Name: telegram_chats_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: market_bot
--

ALTER SEQUENCE public.telegram_chats_id_seq OWNED BY public.telegram_chats.id;


--
-- Name: transactions; Type: TABLE; Schema: public; Owner: market_bot
--

CREATE TABLE public.transactions (
    id integer NOT NULL,
    user_id integer NOT NULL,
    amount numeric(12,2) NOT NULL,
    type character varying(50) NOT NULL,
    payment_id character varying(255),
    payment_status character varying(50),
    payment_method character varying(50),
    description text,
    meta_json jsonb,
    processed_at timestamp with time zone,
    balance_before numeric(12,2) NOT NULL,
    balance_after numeric(12,2) NOT NULL,
    campaign_id integer,
    error_message text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.transactions OWNER TO market_bot;

--
-- Name: TABLE transactions; Type: COMMENT; Schema: public; Owner: market_bot
--

COMMENT ON TABLE public.transactions IS 'Финансовые транзакции пользователей';


--
-- Name: transactions_id_seq; Type: SEQUENCE; Schema: public; Owner: market_bot
--

CREATE SEQUENCE public.transactions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.transactions_id_seq OWNER TO market_bot;

--
-- Name: transactions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: market_bot
--

ALTER SEQUENCE public.transactions_id_seq OWNED BY public.transactions.id;


--
-- Name: user_badges; Type: TABLE; Schema: public; Owner: market_bot
--

CREATE TABLE public.user_badges (
    id integer NOT NULL,
    user_id bigint NOT NULL,
    badge_id integer NOT NULL,
    earned_at timestamp with time zone NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.user_badges OWNER TO market_bot;

--
-- Name: user_badges_id_seq; Type: SEQUENCE; Schema: public; Owner: market_bot
--

CREATE SEQUENCE public.user_badges_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.user_badges_id_seq OWNER TO market_bot;

--
-- Name: user_badges_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: market_bot
--

ALTER SEQUENCE public.user_badges_id_seq OWNED BY public.user_badges.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: market_bot
--

CREATE TABLE public.users (
    id integer NOT NULL,
    telegram_id bigint NOT NULL,
    username character varying(255),
    first_name character varying(255),
    last_name character varying(255),
    language_code character varying(10),
    balance numeric(12,2) NOT NULL,
    plan character varying(50) NOT NULL,
    referral_code character varying(20) NOT NULL,
    referred_by_id bigint,
    is_banned boolean NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    ai_provider character varying(50),
    ai_model character varying(255),
    credits integer DEFAULT 0 NOT NULL,
    ai_generations_used integer DEFAULT 0 NOT NULL,
    plan_expires_at timestamp with time zone,
    notifications_enabled boolean DEFAULT false NOT NULL,
    level integer DEFAULT 1 NOT NULL,
    xp_points integer DEFAULT 0 NOT NULL,
    total_spent numeric(12,2) DEFAULT 0.00 NOT NULL,
    total_earned numeric(12,2) DEFAULT 0.00 NOT NULL,
    streak_days integer DEFAULT 0 NOT NULL
);


ALTER TABLE public.users OWNER TO market_bot;

--
-- Name: TABLE users; Type: COMMENT; Schema: public; Owner: market_bot
--

COMMENT ON TABLE public.users IS 'Пользователи Telegram бота';


--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: market_bot
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO market_bot;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: market_bot
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: b2b_packages id; Type: DEFAULT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.b2b_packages ALTER COLUMN id SET DEFAULT nextval('public.b2b_packages_id_seq'::regclass);


--
-- Name: badges id; Type: DEFAULT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.badges ALTER COLUMN id SET DEFAULT nextval('public.badges_id_seq'::regclass);


--
-- Name: campaigns id; Type: DEFAULT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.campaigns ALTER COLUMN id SET DEFAULT nextval('public.campaigns_id_seq'::regclass);


--
-- Name: channel_ratings id; Type: DEFAULT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.channel_ratings ALTER COLUMN id SET DEFAULT nextval('public.channel_ratings_id_seq'::regclass);


--
-- Name: chat_snapshots id; Type: DEFAULT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.chat_snapshots ALTER COLUMN id SET DEFAULT nextval('public.chat_snapshots_id_seq'::regclass);


--
-- Name: content_flags id; Type: DEFAULT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.content_flags ALTER COLUMN id SET DEFAULT nextval('public.content_flags_id_seq'::regclass);


--
-- Name: crypto_payments id; Type: DEFAULT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.crypto_payments ALTER COLUMN id SET DEFAULT nextval('public.crypto_payments_id_seq'::regclass);


--
-- Name: mailing_logs id; Type: DEFAULT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.mailing_logs ALTER COLUMN id SET DEFAULT nextval('public.mailing_logs_id_seq'::regclass);


--
-- Name: notifications id; Type: DEFAULT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.notifications ALTER COLUMN id SET DEFAULT nextval('public.notifications_id_seq'::regclass);


--
-- Name: payouts id; Type: DEFAULT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.payouts ALTER COLUMN id SET DEFAULT nextval('public.payouts_id_seq'::regclass);


--
-- Name: reviews id; Type: DEFAULT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.reviews ALTER COLUMN id SET DEFAULT nextval('public.reviews_id_seq'::regclass);


--
-- Name: telegram_chats id; Type: DEFAULT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.telegram_chats ALTER COLUMN id SET DEFAULT nextval('public.telegram_chats_id_seq'::regclass);


--
-- Name: transactions id; Type: DEFAULT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.transactions ALTER COLUMN id SET DEFAULT nextval('public.transactions_id_seq'::regclass);


--
-- Name: user_badges id; Type: DEFAULT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.user_badges ALTER COLUMN id SET DEFAULT nextval('public.user_badges_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: market_bot
--

COPY public.alembic_version (version_num) FROM stdin;
20260307_170000
b377ebf742bf
\.


--
-- Data for Name: b2b_packages; Type: TABLE DATA; Schema: public; Owner: market_bot
--

COPY public.b2b_packages (id, name, niche, description, channels_count, guaranteed_reach, min_er, price, discount_pct, is_active, channel_ids, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: badges; Type: TABLE DATA; Schema: public; Owner: market_bot
--

COPY public.badges (id, code, name, description, icon_emoji, xp_reward, category, condition_type, condition_value, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: campaigns; Type: TABLE DATA; Schema: public; Owner: market_bot
--

COPY public.campaigns (id, user_id, title, text, ai_description, status, filters_json, scheduled_at, started_at, completed_at, error_message, total_chats, sent_count, failed_count, skipped_count, cost, created_at, updated_at, topic, header, image_file_id, tracking_url, tracking_short_code, clicks_count) FROM stdin;
\.


--
-- Data for Name: channel_ratings; Type: TABLE DATA; Schema: public; Owner: market_bot
--

COPY public.channel_ratings (id, channel_id, date, subscribers, avg_views, er, reach_score, er_score, growth_score, frequency_score, reliability_score, age_score, total_score, rank_in_topic, fraud_flag, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: chat_snapshots; Type: TABLE DATA; Schema: public; Owner: market_bot
--

COPY public.chat_snapshots (id, chat_id, snapshot_date, subscribers, subscribers_delta, subscribers_delta_pct, avg_views, max_views, min_views, posts_analyzed, er, post_frequency, posts_last_30d, can_post, created_at) FROM stdin;
\.


--
-- Data for Name: content_flags; Type: TABLE DATA; Schema: public; Owner: market_bot
--

COPY public.content_flags (id, campaign_id, categories, flagged_fragments, decision, reviewed_by_id, review_comment, filter_score, llm_analysis, llm_categories, auto_checked, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: crypto_payments; Type: TABLE DATA; Schema: public; Owner: market_bot
--

COPY public.crypto_payments (id, user_id, method, invoice_id, currency, amount, telegram_payment_charge_id, stars_amount, credits, bonus_credits, status, payload, meta_json, credited_at, created_at, updated_at, pay_url) FROM stdin;
2	1	cryptobot	45635310	USDT	3.33333300	\N	\N	300	0	pending	\N	\N	\N	2026-03-01 18:59:45.565587+00	2026-03-01 18:59:45.565588+00	\N
3	1	cryptobot	45636975	USDT	3.33333300	\N	\N	300	0	pending	\N	\N	\N	2026-03-01 19:22:05.487671+00	2026-03-01 19:22:05.487672+00	\N
4	1	cryptobot	45639381	USDT	3.33333300	\N	\N	300	0	pending	\N	\N	\N	2026-03-01 19:55:48.545233+00	2026-03-01 19:55:48.545234+00	\N
5	1	cryptobot	45639710	USDT	3.33333300	\N	\N	300	0	pending	\N	\N	\N	2026-03-01 20:00:52.353981+00	2026-03-01 20:00:52.353983+00	\N
6	1	cryptobot	45639719	USDT	3.33333300	\N	\N	300	0	pending	\N	\N	\N	2026-03-01 20:00:59.8032+00	2026-03-01 20:00:59.803201+00	\N
7	1	cryptobot	45639908	USDT	3.33333300	\N	\N	300	0	pending	\N	\N	\N	2026-03-01 20:03:33.667901+00	2026-03-01 20:03:33.667902+00	\N
8	1	cryptobot	45639936	USDT	3.33333300	\N	\N	300	0	pending	\N	\N	\N	2026-03-01 20:03:51.081668+00	2026-03-01 20:03:51.081688+00	\N
9	1	cryptobot	45649930	USDT	3.33333300	\N	\N	300	0	pending	\N	\N	\N	2026-03-01 23:49:43.795278+00	2026-03-01 23:49:43.795278+00	https://t.me/CryptoBot?start=IVr1PzFNnnGV
10	1	cryptobot	46001364	USDT	3.33333300	\N	\N	300	0	pending	\N	\N	\N	2026-03-06 18:41:47.470646+00	2026-03-06 18:41:47.470646+00	https://t.me/CryptoBot?start=IV4k62VN6i52
\.


--
-- Data for Name: mailing_logs; Type: TABLE DATA; Schema: public; Owner: market_bot
--

COPY public.mailing_logs (id, campaign_id, chat_id, chat_telegram_id, status, error_msg, message_id, retry_count, sent_at, cost, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: notifications; Type: TABLE DATA; Schema: public; Owner: market_bot
--

COPY public.notifications (id, user_id, notification_type, title, message, is_read, campaign_id, transaction_id, error_code, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: payouts; Type: TABLE DATA; Schema: public; Owner: market_bot
--

COPY public.payouts (id, owner_id, channel_id, placement_id, amount, platform_fee, currency, status, wallet_address, tx_hash, paid_at, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: reviews; Type: TABLE DATA; Schema: public; Owner: market_bot
--

COPY public.reviews (id, reviewer_id, reviewee_id, channel_id, placement_id, reviewer_role, score_compliance, score_audience, score_speed, score_material, score_requirements, score_payment, comment, is_hidden, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: telegram_chats; Type: TABLE DATA; Schema: public; Owner: market_bot
--

COPY public.telegram_chats (id, username, telegram_id, title, description, chat_type, topic, is_active, is_public, can_post, member_count, rating, is_scam, is_fake, error_count, deactivate_reason, last_subscribers, last_avg_views, last_er, last_post_frequency, last_parsed_at, parse_error, parse_error_count, created_at, updated_at, subcategory, language, russian_score, complaint_count, last_complaint_at, is_blacklisted, blacklisted_reason, blacklisted_at, consecutive_failures, last_classified_at, llm_confidence, recent_posts, bot_is_admin, admin_added_at, owner_user_id, price_per_post, is_accepting_ads) FROM stdin;
512	rb_ru	1004325579	Russian Business	Сила дерзости и денег \n\nrb.ru\n\nРКН: https://goo.su/FHzPl	channel	business	t	t	f	414975	5	f	f	0	\N	414975	0	0	0	2026-03-06 00:00:00	\N	0	2026-03-06 03:46:26.108829	2026-03-06 03:46:26.108829	\N	ru	1	0	\N	f	\N	\N	0	\N	\N	\N	f	\N	\N	\N	f
513	vedomosti	1075565753	ВЕДОМОСТИ	Деловое издание «Ведомости» – vedomosti.ru \n⚡️Проголосовать: t.me/boost/vedomosti\nСотрудничество — socialmedia@vedomosti.ru, \nРеклама — tg-adv@vedomosti.ru\n\nРегистрация в РКН: clck.ru/3NAdoL	channel	business	t	t	f	84441	5	f	f	0	\N	84441	0	0	0	2026-03-06 00:00:00	\N	0	2026-03-06 03:46:26.108829	2026-03-06 03:46:26.108829	\N	ru	1	0	\N	f	\N	\N	0	\N	\N	\N	f	\N	\N	\N	f
514	kommersant	1038402501	Коммерсантъ	Официальный канал ИД «Коммерсантъ».\n\nНовости бизнеса РФ и мира, финансовые и деловые, о политике, обществе, культуре и спорте.\n\nОбратная связь: kommersant.ru/lk/feedback\nПо вопросам рекламы: advpr@kommersant.ru\n\nПеречень РКН: https://clck.ru/3FFxpT	channel	business	t	t	f	272346	5	f	f	0	\N	272346	0	0	0	2026-03-06 00:00:00	\N	0	2026-03-06 03:46:26.108829	2026-03-06 03:46:26.108829	\N	ru	1	0	\N	f	\N	\N	0	\N	\N	\N	f	\N	\N	\N	f
516	golang_ru	1124938206	Golang Developers — русскоговорящее сообщество	Общаемся на тему разработки для платформы Golang. Обсуждаем идеи и новости, решаем проблемы, учимся вместе.\n\nВакансии и резюме: @golang_jobs\n\nСм. также: @eth_ru, @nodejs_ru, @javascript_jobs	channel	it	t	t	t	1493	5	f	f	0	\N	1493	0	0	0	2026-03-06 00:00:00	\N	0	2026-03-06 03:46:26.108829	2026-03-06 03:46:26.108829	\N	ru	1	0	\N	f	\N	\N	0	\N	\N	\N	f	\N	\N	\N	f
517	javascript_ru	1050591912	javascript_ru	Сообщество любителей самого популярного языка программирования в мире.\n\nЧаты: @frontend_ru @css_ru\nКаналы: @defront @frontendnoteschannel\n\n\nВажно! http://nometa.xyz и http://neprivet.ru	channel	it	t	t	t	1844	5	f	f	0	\N	1844	0	0	0	2026-03-06 00:00:00	\N	0	2026-03-06 03:46:26.108829	2026-03-06 03:46:26.108829	\N	ru	1	0	\N	f	\N	\N	0	\N	\N	\N	f	\N	\N	\N	f
518	frontend_ru	1062487497	Frontend_ru	Русскоговорящее сообщество фронтенд разработчиков\n\nКаналы: @frontendnoteschannel @defront\nЧаты: @bem_ru @javascript_ru @css_ru\n\nВажно! http://nometa.xyz	channel	it	t	t	t	2811	5	f	f	0	\N	2811	0	0	0	2026-03-06 00:00:00	\N	0	2026-03-06 03:46:26.108829	2026-03-06 03:46:26.108829	\N	ru	1	0	\N	f	\N	\N	0	\N	\N	\N	f	\N	\N	\N	f
519	devops_ru	1030317489	DevOps — русскоговорящее сообщество	Общаемся на темы DevOps, мониторинга, метрикам и облакам. Новости.\n\nСм. также: @kubernetes_ru, @docker_ru, @ceph_ru, @openstack_ru\n\nFAQ и правила: https://git.io/JtnWb\n\nВакансии и поиск работы: @devops_jobs	channel	it	t	t	t	19373	5	f	f	0	\N	19373	0	0	0	2026-03-06 00:00:00	\N	0	2026-03-06 03:46:26.108829	2026-03-06 03:46:26.108829	\N	ru	1	0	\N	f	\N	\N	0	\N	\N	\N	f	\N	\N	\N	f
520	docker_ru	1088804534	Docker — русскоговорящее сообщество	Обсуждаем вопросы, посвященные Docker🐳, Docker Swarm и всей экосистеме. Обмениваем идеями, новостями и решаем пробемы.\n\nВам могут быть полезны: @coreos_ru, @kubernetes_ru, @devops_ru, @rkt_ru\n\nРекомендуем сразу отключить уведомления для удобства	channel	it	t	t	t	11757	5	f	f	0	\N	11757	0	0	0	2026-03-06 00:00:00	\N	0	2026-03-06 03:46:26.108829	2026-03-06 03:46:26.108829	\N	ru	1	0	\N	f	\N	\N	0	\N	\N	\N	f	\N	\N	\N	f
521	kubernetes_ru	1096347276	Kubernetes — русскоговорящее сообщество	Общаемся на темы, посвященные Kubernetes, конфигурации и возможностям. Новости, вопросы, идеи и т.д.\n\nСм. также:  @docker_ru, @devops_ru, @ceph_ru, @openstack_ru\n\nВакансии и поиск работы: @devops_jobs\n\nРекомендуем сразу отключить уведомления.	channel	it	t	t	t	11622	5	f	f	0	\N	11622	0	0	0	2026-03-06 00:00:00	\N	0	2026-03-06 03:46:26.108829	2026-03-06 03:46:26.108829	\N	ru	1	0	\N	f	\N	\N	0	\N	\N	\N	f	\N	\N	\N	f
522	smm_ru	1021645597	Smm room	Про маркетинг в целом и смм в частности, digital и журналистику от @Rytov 👤\n\nДля полного погружения будет полезна моя записная книжка ➖ «Костя шарит» @smmtg\n\nЧат: @smmkitchen	channel	marketing	t	t	f	558	5	f	f	0	\N	558	0	0	0	2026-03-06 00:00:00	\N	0	2026-03-06 03:46:26.108829	2026-03-06 03:46:26.108829	\N	ru	1	0	\N	f	\N	\N	0	\N	\N	\N	f	\N	\N	\N	f
523	targetolog	1831354176	ТАРГЕТОЛОГ		channel	marketing	f	f	f	17	5	f	f	0	\N	17	0	0	0	2026-03-06 00:00:00	\N	0	2026-03-06 03:46:26.108829	2026-03-06 03:46:26.108829	\N	ru	1	0	\N	f	\N	\N	0	\N	\N	\N	f	\N	\N	\N	f
524	content_marketing	1014105953	Content Marketing		channel	marketing	f	t	f	28	5	f	f	0	\N	28	0	0	0	2026-03-06 00:00:00	\N	0	2026-03-06 03:46:26.108829	2026-03-06 03:46:26.108829	\N	ru	1	0	\N	f	\N	\N	0	\N	\N	\N	f	\N	\N	\N	f
525	rian_ru	1101170442	РИА Новости	Главные Новости РИА\n\nАвторы канала - наши корреспонденты в России и за рубежом. Мы рассказываем о том, что видим сами.\n\nРегистрация в перечне РКН www.gosuslugi.ru/snet/678637f9506f967728faabaa	channel	news	t	t	f	3179055	5	f	f	0	\N	3179055	0	0	0	2026-03-06 00:00:00	\N	0	2026-03-06 03:46:26.108829	2026-03-06 03:46:26.108829	\N	ru	1	0	\N	f	\N	\N	0	\N	\N	\N	f	\N	\N	\N	f
515	tass_agency	1050820672	ТАСС	Главные новости агентства ТАСС https://tass.ru\n\nРегистрация в перечне РКН: https://knd.gov.ru/license?id=673f0f77290fef0e012d86a9&registryType=bloggersPermission	channel	news	t	t	f	575739	5	f	f	0	\N	575739	0	0	0	2026-03-06 00:00:00	\N	0	2026-03-06 03:46:26.108829	2026-03-06 03:46:26.108829	\N	ru	1	0	\N	f	\N	\N	0	\N	\N	\N	f	\N	\N	\N	f
526	lenta_ru	1006757604	lenta_ru		channel	news	f	t	f	57	5	f	f	0	\N	57	0	0	0	2026-03-06 00:00:00	\N	0	2026-03-06 03:46:26.108829	2026-03-06 03:46:26.108829	\N	ru	1	0	\N	f	\N	\N	0	\N	\N	\N	f	\N	\N	\N	f
506	popcorn_today	2289627285	Popcorn Today 🍿	Your daily portion of popping crypto news!\n\n\nFor partnerships and advertising inquiries, please fill out this form - https://forms.gle/Z68LPq8ge8UJgtvo6 📝	channel	other	t	t	f	3759318	5	f	f	0	\N	3759318	0	0	0	2026-03-03 00:00:00	\N	0	2026-03-02 12:23:37.033612	2026-03-03 04:38:29.296826	\N	ru	1	0	\N	f	\N	\N	0	\N	\N	\N	f	\N	\N	\N	f
509	blumcrypto	2039438207	Blum: All Crypto – One App	Your easy, fun crypto trading app for buying and trading any crypto on the market. \n  📱 App: @Blum\n  🤖 Trading Bot: @BlumCryptoTradingBot\n  🆘 Help: @BlumSupport\n  💬 Chat: @BlumCrypto_Chat	channel	other	t	t	f	21159415	7	f	f	0	\N	21159415	0	0	0	2026-03-03 00:00:00	\N	0	2026-03-02 12:23:41.700729	2026-03-03 04:38:29.296826	\N	ru	1	0	\N	f	\N	\N	0	\N	\N	\N	f	\N	\N	\N	f
527	holodmedia	1184122942	Холод	holod.media\n\n«Холод» — это независимое российское издание, запущенное в августе 2019 года.\n\nСвязаться с нами: holod@holod.media\n\nБот для связи в телеграме: @HotHolodBot\n\nРеклама и партнерство: ads@holod.media\n\nПоддержите нас: https://holod.help	channel	news	t	t	f	59938	5	f	f	0	\N	59938	0	0	0	2026-03-06 00:00:00	\N	0	2026-03-06 03:46:26.108829	2026-03-06 03:46:26.108829	\N	ru	1	0	\N	f	\N	\N	0	\N	\N	\N	f	\N	\N	\N	f
528	verstka	1848999542	FIGMA — Code Review верстки	Макеты сайтов в Figma.\n\nВы можете взять макет в верстку и получить Code Review от Senior Frontend разработчиков.\n\nКанал помогает начинающим Веб разработчикам.	channel	news	t	f	f	2511	5	f	f	0	\N	2511	0	0	0	2026-03-06 00:00:00	\N	0	2026-03-06 03:46:26.108829	2026-03-06 03:46:26.108829	\N	ru	1	0	\N	f	\N	\N	0	\N	\N	\N	f	\N	\N	\N	f
529	geekbrains	1656452550	Geekbrains		channel	education	f	f	f	25	5	f	f	0	\N	25	0	0	0	2026-03-06 00:00:00	\N	0	2026-03-06 03:46:26.108829	2026-03-06 03:46:26.108829	\N	ru	1	0	\N	f	\N	\N	0	\N	\N	\N	f	\N	\N	\N	f
530	postnauka	1022687893	ПостНаука	https://postnauka.org\n\nПо вопросам сотрудничества: https://postnauka.org/link/letsdance_tg\n\nПостНаука на других площадках: https://postnauka.org/link/hipolink	channel	education	t	t	f	20459	5	f	f	0	\N	20459	0	0	0	2026-03-06 00:00:00	\N	0	2026-03-06 03:46:26.108829	2026-03-06 03:46:26.108829	\N	ru	1	0	\N	f	\N	\N	0	\N	\N	\N	f	\N	\N	\N	f
531	defi_ru	1479496675	DeFi RU	Новостной канал - t.me/defi_news	channel	crypto	f	t	t	7	5	f	f	0	\N	7	0	0	0	2026-03-06 00:00:00	\N	0	2026-03-06 03:46:26.108829	2026-03-06 03:46:26.108829	\N	ru	1	0	\N	f	\N	\N	0	\N	\N	\N	f	\N	\N	\N	f
532	nft_ru	1291308992	NFT & Метавселенные	Группа для обсуждения вопросов, связанных с темами NFT, виртуальных вселенных, токенизации арт-объектов и т.п.\n\n#crypto #nft #metaverse #defi #art\n\nEnglish: https://t.me/nftdao	channel	crypto	f	t	t	80	5	f	f	0	\N	80	0	0	0	2026-03-06 00:00:00	\N	0	2026-03-06 03:46:26.108829	2026-03-06 03:46:26.108829	\N	ru	1	0	\N	f	\N	\N	0	\N	\N	\N	f	\N	\N	\N	f
533	zdorovie_ru	1694059709	Моя Поликлиника	Поможем вам позаботиться о своем здоровье	channel	health	t	t	f	275	5	f	f	0	\N	275	0	0	0	2026-03-06 00:00:00	\N	0	2026-03-06 03:46:26.108829	2026-03-06 03:46:26.108829	\N	ru	1	0	\N	f	\N	\N	0	\N	\N	\N	f	\N	\N	\N	f
534	travel_ru	1006926158	Travel		channel	lifestyle	f	t	f	8	5	f	f	0	\N	8	0	0	0	2026-03-06 00:00:00	\N	0	2026-03-06 03:46:26.108829	2026-03-06 03:46:26.108829	\N	ru	1	0	\N	f	\N	\N	0	\N	\N	\N	f	\N	\N	\N	f
535	food_ru	2420458398	x5group (продается)	Выкупить никнейм @x5group: https://fragment.com/username/x5group\n\nКонтакт для связи: @x5ferz	channel	lifestyle	f	f	f	37	5	f	f	0	\N	37	0	0	0	2026-03-06 00:00:00	\N	0	2026-03-06 03:46:26.108829	2026-03-06 03:46:26.108829	\N	ru	1	0	\N	f	\N	\N	0	\N	\N	\N	f	\N	\N	\N	f
536	design_ru	1067492853	Дизайн, фриланс, логотипы, визитки, макеты	фриланс, логотипы, визитки, макеты	channel	lifestyle	f	t	t	35	5	f	f	0	\N	35	0	0	0	2026-03-06 00:00:00	\N	0	2026-03-06 03:46:26.108829	2026-03-06 03:46:26.108829	\N	ru	1	0	\N	f	\N	\N	0	\N	\N	\N	f	\N	\N	\N	f
537	cinema_ru	1399307519	Кино	Заказываем \n@jasurbek1155	channel	lifestyle	f	t	f	13	5	f	f	0	\N	13	0	0	0	2026-03-06 00:00:00	\N	0	2026-03-06 03:46:26.108829	2026-03-06 03:46:26.108829	\N	ru	1	0	\N	f	\N	\N	0	\N	\N	\N	f	\N	\N	\N	f
510	rndmciub	1812628545	rndm.club	Official channel of rndm.club\nContact: info@rndm.club\nMoscow, Nastavnichesky Lane, 13–15с3	channel	other	t	t	f	4794	5	f	f	0	\N	4794	0	0	0	2026-03-03 00:00:00	\N	0	2026-03-02 13:20:21.25472	2026-03-03 04:38:05.48503	\N	ru	1	0	\N	f	\N	\N	0	\N	\N	\N	f	\N	\N	\N	f
511	d_woofs	1337919764	WOOFS DВИЖ Party+After 🐺🔞	Анонсы мероприятий. Релизы. Фото и видео отчеты с вечеринок.\n\n#спискиотвуфс\n@dashawoofs\n+79679871230\nДонаты сюда не 2200700431881837	channel	other	t	t	f	471	5	f	f	0	\N	471	0	0	0	2026-03-03 00:00:00	\N	0	2026-03-02 13:20:26.488506	2026-03-03 04:38:07.116792	\N	ru	1	0	\N	f	\N	\N	0	\N	\N	\N	f	\N	\N	\N	f
497	python	1050982793	Python	You will be muted until you read the rules. Read them! @Rules_for_Python\n\nA group about the Python programming language.\n\nOfftopic things go here: @pythonofftopic\n\nResources to learn python: @pythonres\n\nGroup for Hy: @hylang\n\nSelenium: @SeleniumPython	channel	it	t	t	f	111845	5	f	f	0	\N	111845	0	0	0	2026-03-02 00:00:00	\N	0	2026-03-02 01:15:12.186031	2026-03-02 16:39:42.428038	programming	ru	1	0	\N	f	\N	\N	0	\N	\N	\N	f	\N	\N	\N	f
495	movies	1012043593	Movies		channel	other	t	t	f	5837	5	f	f	0	\N	5837	0	0	0	2026-03-01 00:00:00	\N	0	2026-03-01 03:00:46.467618	2026-03-01 03:00:46.467618	\N	ru	1	0	\N	f	\N	\N	0	\N	\N	\N	f	\N	\N	\N	f
496	entertainment	1009434980	Entertainment 🎬	Best official trailers and good taste in movies.\n\nMovies, Films, Cinemas, Pictures, TV Shows and Games.\n\nBoost: https://t.me/boost/Entertainment	channel	it	t	t	f	28574	5	f	f	0	\N	28574	0	0	0	2026-03-01 00:00:00	\N	0	2026-03-01 03:00:50.672246	2026-03-01 03:00:50.672246	\N	ru	1	0	\N	f	\N	\N	0	\N	\N	\N	f	\N	\N	\N	f
498	golang	1003436297	Go	// admin @denniselite\ngo func() { channel <- news }()\nnews := <-channel\nfmt.Sprintf("%s", news)	channel	it	t	t	f	19356	5	f	f	0	\N	19356	0	0	0	2026-03-02 00:00:00	\N	0	2026-03-02 01:15:17.52402	2026-03-02 01:15:17.52402	\N	ru	1	0	\N	f	\N	\N	0	\N	\N	\N	f	\N	\N	\N	f
499	mkhusnullin	1519103464	Марат Хуснуллин	Заместитель Председателя Правительства Российской Федерации\n\n\n\n\n5144266810	channel	other	t	t	f	219689	7	f	f	0	\N	219689	0	0	0	2026-03-03 00:00:00	\N	0	2026-03-02 12:22:53.223791	2026-03-03 03:16:23.982502	\N	ru	1	0	\N	f	\N	\N	0	\N	\N	\N	f	\N	\N	\N	f
500	finnext_official	2422150730	FINNEXT – форум финансовых инноваций	Канал Форума финансовых инноваций FINNEXT (https://clck.ru/3FJRmV) и Премии FINNEXT (https://clck.ru/3FJRfo)\n\nВыступления или партнерства: @yulia_gum\nУчастие: @SMelnik22\n\nКанал ведет ООО «Регламент», ИНН 7708323273 – организатор FINNEXT и Премии FINNEXT	channel	финансы	t	t	f	961	5	f	f	0	\N	961	0	0	0	2026-03-03 00:00:00	\N	0	2026-03-02 12:22:53.223791	2026-03-03 04:38:38.697617	\N	ru	1	0	\N	f	\N	\N	0	\N	\N	\N	f	\N	\N	\N	f
503	ibelieveicanf	1993303200	Айбелив Айкенфлаев	Родился в Казахстане 🇰🇿 \nЖиву в России 🇷🇺 \nВ розыске за кражу мемов 😩 \nВерю, что взлечу 🚀\n\nПо вопросам рекламы, кумыса и колбасы из конины - @manager_ibelive \n\nПредложка - @Ibelievechik_bot\n\nРегистрация в перечне владельцев страниц в соцсетях - 5349754817	channel	other	t	t	f	43248	5	f	f	0	\N	43248	0	0	0	2026-03-07 00:00:00	\N	0	2026-03-02 12:23:00.494931	2026-03-07 03:16:48.558112	\N	mixed	0.5	0	\N	f	\N	\N	0	\N	\N	\N	f	\N	\N	\N	f
501	amwineru	1345705498	Ароматный Мир	18+. Более 1000 магазинов food&wine по всей стране.\n\nОфициальный сайт - amwine.ru\n\nСтать франчайзи - https://franch.amwine.ru/\n\nВыпустить карту, проверить бонусный баланс - @AromatnymirBot\n\nРКН https://clck.ru/3JSWhw	channel	новости	t	t	f	47030	5	f	f	0	\N	47030	0	0	0	2026-03-02 00:00:00	\N	0	2026-03-02 12:22:53.223791	2026-03-02 12:35:35.126405	\N	ru	1	0	\N	f	\N	\N	0	\N	\N	\N	f	\N	\N	\N	f
505	freecryptosfaucets	1756701118	Free Crypto	Welcome to Cryptosfaucets' Official Telegram	channel	other	t	t	f	27320	5	f	f	0	\N	27320	0	0	0	2026-03-03 00:00:00	\N	0	2026-03-02 12:23:28.55401	2026-03-03 01:35:36.4248	\N	ru	1	0	\N	f	\N	\N	0	\N	\N	\N	f	\N	\N	\N	f
507	blumcrypto_memepad	2417177935	Blum Memepad	The ultimate platform that lets you create, launch, and grow your very own meme token in just a few clicks. \n\nBlum Memepad does not recommend that any cryptocurrency should be created, bought, sold, or held, and is not liable for any losses\n🆘 @BlumSuppor	channel	other	t	t	f	3391256	7	f	f	0	\N	3391256	0	0	0	2026-03-03 00:00:00	\N	0	2026-03-02 12:23:41.700729	2026-03-03 01:36:34.419062	\N	ru	1	0	\N	f	\N	\N	0	\N	\N	\N	f	\N	\N	\N	f
502	dailydvizh	1177339059	DAILY DVIZH - твой гайд по клубам, фестивалям, выставкам Москвы и Питера	♦️  Афиши лучших вечеринок, концертов, фестивалей, обзоры выставок Москвы и Питера. Фото / видео репортажи.\n\n♦️  Подборки тусовок и распродажа проходок с большими скидками! \n\n▪️ Анонсы/подборки  @scvx9\n▪️ Билеты/проходки @nikkizi	channel	it	t	t	f	18722	5	f	f	0	\N	18722	0	0	0	2026-03-02 00:00:00	\N	0	2026-03-02 12:22:55.133048	2026-03-02 12:36:41.545488	\N	ru	1	0	\N	f	\N	\N	0	\N	\N	\N	f	\N	\N	\N	f
508	cheatkott	2174452486	CHEATKOTT - Your Daily News	We’re your go-to infotainment hub, keeping you updated on everything Web 3.0, business, fashion, lifestyle, and education.\n\n@CheatKott_Godfather	channel	it	t	t	f	3253028	5	f	f	0	\N	3253028	0	0	0	2026-03-03 00:00:00	\N	0	2026-03-02 12:23:41.700729	2026-03-03 04:38:29.296826	\N	ru	1	0	\N	f	\N	\N	0	\N	\N	\N	f	\N	\N	\N	f
504	gaztelegram	1401871758	Gazgolder club	Информация / Резерв: +7 (991) 265-03-55\n\nРасписание мероприятий и билеты по ссылке: www.gazgolderclub.ru\n\n18+\n\n#gazgolderclub #nightclub #music\n\nАдрес: Нижний Сусальный пер, 5 стр 26.	channel	other	t	t	f	10034	7	f	f	0	\N	10034	0	0	0	2026-03-03 00:00:00	\N	0	2026-03-02 12:23:05.61215	2026-03-03 04:38:49.104872	\N	ru	1	0	\N	f	\N	\N	0	\N	\N	\N	f	\N	\N	\N	f
494	science	1091087098	Science in telegram	#Science telegram channel \nBest science content in telegram\n\n@Fsnewsbot - our business cards scanner \n\nOur subscribers geo: https://t.me/science/3736\nAds: @ficusoid	channel	Другое	t	t	f	129370	5	f	f	0	\N	129370	0	0	0	2026-03-01 00:00:00	\N	0	2026-03-01 03:00:40.223457	2026-03-04 15:57:51.623128		ru	1	0	\N	f	\N	\N	0	2026-03-04 15:57:51.651763+00	0	\N	f	\N	\N	\N	f
\.


--
-- Data for Name: transactions; Type: TABLE DATA; Schema: public; Owner: market_bot
--

COPY public.transactions (id, user_id, amount, type, payment_id, payment_status, payment_method, description, meta_json, processed_at, balance_before, balance_after, campaign_id, error_message, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: user_badges; Type: TABLE DATA; Schema: public; Owner: market_bot
--

COPY public.user_badges (id, user_id, badge_id, earned_at, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: market_bot
--

COPY public.users (id, telegram_id, username, first_name, last_name, language_code, balance, plan, referral_code, referred_by_id, is_banned, is_active, created_at, updated_at, ai_provider, ai_model, credits, ai_generations_used, plan_expires_at, notifications_enabled, level, xp_points, total_spent, total_earned, streak_days) FROM stdin;
5	123456789	testuser1	Тестовый 1	\N	ru	0.00	starter	TEST1	\N	f	t	2026-03-03 18:46:33.678411+00	2026-03-03 18:46:33.678411+00	\N	\N	100	0	\N	f	1	0	0.00	0.00	0
6	987654321	testuser2	Тестовый 2	\N	ru	0.00	pro	TEST2	\N	f	t	2026-03-03 18:46:33.678411+00	2026-03-03 18:46:33.678411+00	\N	\N	500	0	\N	f	1	0	0.00	0.00	0
10	5334943139	Vairin	~	\N	ru	0.00	free	8C35C4BA	\N	f	t	2026-03-03 18:55:56.16486+00	2026-03-03 18:55:56.16486+00	\N	\N	0	0	\N	f	1	0	0.00	0.00	0
1	1333213303	adbelin	Александр	ППК ЕЗ Белин	ru	0.00	business	EEA4232E	\N	f	t	2026-02-27 13:18:19.534031+00	2026-03-03 18:31:42.492374+00	\N	\N	0	0	2026-04-02 18:31:42.488694+00	f	1	0	0.00	0.00	0
11	5947269144	Muallim012	Bobo	\N	uz	0.00	free	E1BC3350	\N	f	t	2026-03-07 18:50:00.681768+00	2026-03-07 18:50:00.681768+00	\N	\N	0	0	\N	f	1	0	0.00	0.00	0
\.


--
-- Name: b2b_packages_id_seq; Type: SEQUENCE SET; Schema: public; Owner: market_bot
--

SELECT pg_catalog.setval('public.b2b_packages_id_seq', 1, false);


--
-- Name: badges_id_seq; Type: SEQUENCE SET; Schema: public; Owner: market_bot
--

SELECT pg_catalog.setval('public.badges_id_seq', 1, false);


--
-- Name: campaigns_id_seq; Type: SEQUENCE SET; Schema: public; Owner: market_bot
--

SELECT pg_catalog.setval('public.campaigns_id_seq', 1, false);


--
-- Name: channel_ratings_id_seq; Type: SEQUENCE SET; Schema: public; Owner: market_bot
--

SELECT pg_catalog.setval('public.channel_ratings_id_seq', 1, false);


--
-- Name: chat_snapshots_id_seq; Type: SEQUENCE SET; Schema: public; Owner: market_bot
--

SELECT pg_catalog.setval('public.chat_snapshots_id_seq', 92, true);


--
-- Name: content_flags_id_seq; Type: SEQUENCE SET; Schema: public; Owner: market_bot
--

SELECT pg_catalog.setval('public.content_flags_id_seq', 1, false);


--
-- Name: crypto_payments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: market_bot
--

SELECT pg_catalog.setval('public.crypto_payments_id_seq', 10, true);


--
-- Name: mailing_logs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: market_bot
--

SELECT pg_catalog.setval('public.mailing_logs_id_seq', 1, false);


--
-- Name: notifications_id_seq; Type: SEQUENCE SET; Schema: public; Owner: market_bot
--

SELECT pg_catalog.setval('public.notifications_id_seq', 1, false);


--
-- Name: payouts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: market_bot
--

SELECT pg_catalog.setval('public.payouts_id_seq', 1, false);


--
-- Name: reviews_id_seq; Type: SEQUENCE SET; Schema: public; Owner: market_bot
--

SELECT pg_catalog.setval('public.reviews_id_seq', 1, false);


--
-- Name: telegram_chats_id_seq; Type: SEQUENCE SET; Schema: public; Owner: market_bot
--

SELECT pg_catalog.setval('public.telegram_chats_id_seq', 537, true);


--
-- Name: transactions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: market_bot
--

SELECT pg_catalog.setval('public.transactions_id_seq', 1, false);


--
-- Name: user_badges_id_seq; Type: SEQUENCE SET; Schema: public; Owner: market_bot
--

SELECT pg_catalog.setval('public.user_badges_id_seq', 1, false);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: market_bot
--

SELECT pg_catalog.setval('public.users_id_seq', 11, true);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: b2b_packages b2b_packages_pkey; Type: CONSTRAINT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.b2b_packages
    ADD CONSTRAINT b2b_packages_pkey PRIMARY KEY (id);


--
-- Name: badges badges_pkey; Type: CONSTRAINT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.badges
    ADD CONSTRAINT badges_pkey PRIMARY KEY (id);


--
-- Name: campaigns campaigns_pkey; Type: CONSTRAINT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.campaigns
    ADD CONSTRAINT campaigns_pkey PRIMARY KEY (id);


--
-- Name: channel_ratings channel_ratings_pkey; Type: CONSTRAINT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.channel_ratings
    ADD CONSTRAINT channel_ratings_pkey PRIMARY KEY (id);


--
-- Name: chat_snapshots chat_snapshots_pkey; Type: CONSTRAINT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.chat_snapshots
    ADD CONSTRAINT chat_snapshots_pkey PRIMARY KEY (id);


--
-- Name: content_flags content_flags_pkey; Type: CONSTRAINT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.content_flags
    ADD CONSTRAINT content_flags_pkey PRIMARY KEY (id);


--
-- Name: crypto_payments crypto_payments_pkey; Type: CONSTRAINT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.crypto_payments
    ADD CONSTRAINT crypto_payments_pkey PRIMARY KEY (id);


--
-- Name: mailing_logs mailing_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.mailing_logs
    ADD CONSTRAINT mailing_logs_pkey PRIMARY KEY (id);


--
-- Name: notifications notifications_pkey; Type: CONSTRAINT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_pkey PRIMARY KEY (id);


--
-- Name: payouts payouts_pkey; Type: CONSTRAINT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.payouts
    ADD CONSTRAINT payouts_pkey PRIMARY KEY (id);


--
-- Name: reviews reviews_pkey; Type: CONSTRAINT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_pkey PRIMARY KEY (id);


--
-- Name: telegram_chats telegram_chats_pkey; Type: CONSTRAINT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.telegram_chats
    ADD CONSTRAINT telegram_chats_pkey PRIMARY KEY (id);


--
-- Name: telegram_chats telegram_chats_telegram_id_key; Type: CONSTRAINT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.telegram_chats
    ADD CONSTRAINT telegram_chats_telegram_id_key UNIQUE (telegram_id);


--
-- Name: telegram_chats telegram_chats_username_key; Type: CONSTRAINT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.telegram_chats
    ADD CONSTRAINT telegram_chats_username_key UNIQUE (username);


--
-- Name: transactions transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_pkey PRIMARY KEY (id);


--
-- Name: channel_ratings uq_channel_rating_date; Type: CONSTRAINT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.channel_ratings
    ADD CONSTRAINT uq_channel_rating_date UNIQUE (channel_id, date);


--
-- Name: chat_snapshots uq_chat_snapshot_date; Type: CONSTRAINT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.chat_snapshots
    ADD CONSTRAINT uq_chat_snapshot_date UNIQUE (chat_id, snapshot_date);


--
-- Name: content_flags uq_content_flags_campaign_id; Type: CONSTRAINT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.content_flags
    ADD CONSTRAINT uq_content_flags_campaign_id UNIQUE (campaign_id);


--
-- Name: mailing_logs uq_mailing_logs_campaign_chat; Type: CONSTRAINT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.mailing_logs
    ADD CONSTRAINT uq_mailing_logs_campaign_chat UNIQUE (campaign_id, chat_telegram_id);


--
-- Name: reviews uq_reviewer_placement; Type: CONSTRAINT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT uq_reviewer_placement UNIQUE (reviewer_id, placement_id);


--
-- Name: transactions uq_transactions_payment_id; Type: CONSTRAINT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT uq_transactions_payment_id UNIQUE (payment_id);


--
-- Name: user_badges uq_user_badge; Type: CONSTRAINT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.user_badges
    ADD CONSTRAINT uq_user_badge UNIQUE (user_id, badge_id);


--
-- Name: users uq_users_telegram_id; Type: CONSTRAINT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT uq_users_telegram_id UNIQUE (telegram_id);


--
-- Name: user_badges user_badges_pkey; Type: CONSTRAINT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.user_badges
    ADD CONSTRAINT user_badges_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: ix_b2b_packages_is_active; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_b2b_packages_is_active ON public.b2b_packages USING btree (is_active);


--
-- Name: ix_b2b_packages_niche; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_b2b_packages_niche ON public.b2b_packages USING btree (niche);


--
-- Name: ix_badges_code; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE UNIQUE INDEX ix_badges_code ON public.badges USING btree (code);


--
-- Name: ix_campaigns_scheduled_at; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_campaigns_scheduled_at ON public.campaigns USING btree (scheduled_at);


--
-- Name: ix_campaigns_scheduled_status; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_campaigns_scheduled_status ON public.campaigns USING btree (scheduled_at, status);


--
-- Name: ix_campaigns_status; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_campaigns_status ON public.campaigns USING btree (status);


--
-- Name: ix_campaigns_tracking_short_code; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_campaigns_tracking_short_code ON public.campaigns USING btree (tracking_short_code);


--
-- Name: ix_campaigns_user_id; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_campaigns_user_id ON public.campaigns USING btree (user_id);


--
-- Name: ix_campaigns_user_status; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_campaigns_user_status ON public.campaigns USING btree (user_id, status);


--
-- Name: ix_channel_ratings_channel_id; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_channel_ratings_channel_id ON public.channel_ratings USING btree (channel_id);


--
-- Name: ix_channel_ratings_date; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_channel_ratings_date ON public.channel_ratings USING btree (date);


--
-- Name: ix_channel_ratings_fraud_flag; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_channel_ratings_fraud_flag ON public.channel_ratings USING btree (fraud_flag);


--
-- Name: ix_channel_ratings_total_score; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_channel_ratings_total_score ON public.channel_ratings USING btree (total_score);


--
-- Name: ix_content_flags_campaign_id; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE UNIQUE INDEX ix_content_flags_campaign_id ON public.content_flags USING btree (campaign_id);


--
-- Name: ix_content_flags_categories; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_content_flags_categories ON public.content_flags USING gin (categories);


--
-- Name: ix_content_flags_decision; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_content_flags_decision ON public.content_flags USING btree (decision);


--
-- Name: ix_content_flags_reviewed_by_id; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_content_flags_reviewed_by_id ON public.content_flags USING btree (reviewed_by_id);


--
-- Name: ix_crypto_payments_credited_at; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_crypto_payments_credited_at ON public.crypto_payments USING btree (credited_at);


--
-- Name: ix_crypto_payments_invoice_id; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE UNIQUE INDEX ix_crypto_payments_invoice_id ON public.crypto_payments USING btree (invoice_id);


--
-- Name: ix_crypto_payments_status; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_crypto_payments_status ON public.crypto_payments USING btree (status);


--
-- Name: ix_crypto_payments_user_id; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_crypto_payments_user_id ON public.crypto_payments USING btree (user_id);


--
-- Name: ix_crypto_payments_user_status; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_crypto_payments_user_status ON public.crypto_payments USING btree (user_id, status);


--
-- Name: ix_mailing_logs_campaign_id; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_mailing_logs_campaign_id ON public.mailing_logs USING btree (campaign_id);


--
-- Name: ix_mailing_logs_chat_id; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_mailing_logs_chat_id ON public.mailing_logs USING btree (chat_id);


--
-- Name: ix_mailing_logs_chat_telegram; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_mailing_logs_chat_telegram ON public.mailing_logs USING btree (chat_telegram_id);


--
-- Name: ix_mailing_logs_chat_telegram_id; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_mailing_logs_chat_telegram_id ON public.mailing_logs USING btree (chat_telegram_id);


--
-- Name: ix_mailing_logs_sent_at; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_mailing_logs_sent_at ON public.mailing_logs USING btree (sent_at);


--
-- Name: ix_mailing_logs_status; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_mailing_logs_status ON public.mailing_logs USING btree (status);


--
-- Name: ix_mailing_logs_status_campaign; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_mailing_logs_status_campaign ON public.mailing_logs USING btree (status, campaign_id);


--
-- Name: ix_notifications_campaign_id; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_notifications_campaign_id ON public.notifications USING btree (campaign_id);


--
-- Name: ix_notifications_is_read; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_notifications_is_read ON public.notifications USING btree (is_read);


--
-- Name: ix_notifications_notification_type; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_notifications_notification_type ON public.notifications USING btree (notification_type);


--
-- Name: ix_notifications_transaction_id; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_notifications_transaction_id ON public.notifications USING btree (transaction_id);


--
-- Name: ix_notifications_user_id; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_notifications_user_id ON public.notifications USING btree (user_id);


--
-- Name: ix_payouts_channel_id; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_payouts_channel_id ON public.payouts USING btree (channel_id);


--
-- Name: ix_payouts_owner_id; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_payouts_owner_id ON public.payouts USING btree (owner_id);


--
-- Name: ix_payouts_paid_at; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_payouts_paid_at ON public.payouts USING btree (paid_at);


--
-- Name: ix_payouts_placement_id; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE UNIQUE INDEX ix_payouts_placement_id ON public.payouts USING btree (placement_id);


--
-- Name: ix_payouts_status; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_payouts_status ON public.payouts USING btree (status);


--
-- Name: ix_reviews_channel_id; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_reviews_channel_id ON public.reviews USING btree (channel_id);


--
-- Name: ix_reviews_is_hidden; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_reviews_is_hidden ON public.reviews USING btree (is_hidden);


--
-- Name: ix_reviews_placement_id; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE UNIQUE INDEX ix_reviews_placement_id ON public.reviews USING btree (placement_id);


--
-- Name: ix_reviews_reviewee_id; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_reviews_reviewee_id ON public.reviews USING btree (reviewee_id);


--
-- Name: ix_reviews_reviewer_id; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_reviews_reviewer_id ON public.reviews USING btree (reviewer_id);


--
-- Name: ix_telegram_chats_is_active; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_telegram_chats_is_active ON public.telegram_chats USING btree (is_active);


--
-- Name: ix_telegram_chats_is_blacklisted; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_telegram_chats_is_blacklisted ON public.telegram_chats USING btree (is_blacklisted);


--
-- Name: ix_telegram_chats_member_count; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_telegram_chats_member_count ON public.telegram_chats USING btree (member_count);


--
-- Name: ix_telegram_chats_rating; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_telegram_chats_rating ON public.telegram_chats USING btree (rating);


--
-- Name: ix_telegram_chats_subcategory; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_telegram_chats_subcategory ON public.telegram_chats USING btree (subcategory);


--
-- Name: ix_telegram_chats_topic_active; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_telegram_chats_topic_active ON public.telegram_chats USING btree (topic, is_active);


--
-- Name: ix_transactions_campaign_id; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_transactions_campaign_id ON public.transactions USING btree (campaign_id);


--
-- Name: ix_transactions_created; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_transactions_created ON public.transactions USING btree (created_at);


--
-- Name: ix_transactions_payment_id; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE UNIQUE INDEX ix_transactions_payment_id ON public.transactions USING btree (payment_id);


--
-- Name: ix_transactions_processed_at; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_transactions_processed_at ON public.transactions USING btree (processed_at);


--
-- Name: ix_transactions_type; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_transactions_type ON public.transactions USING btree (type);


--
-- Name: ix_transactions_user_id; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_transactions_user_id ON public.transactions USING btree (user_id);


--
-- Name: ix_transactions_user_type; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_transactions_user_type ON public.transactions USING btree (user_id, type);


--
-- Name: ix_user_badges_badge_id; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_user_badges_badge_id ON public.user_badges USING btree (badge_id);


--
-- Name: ix_user_badges_user_id; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_user_badges_user_id ON public.user_badges USING btree (user_id);


--
-- Name: ix_users_is_active; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_users_is_active ON public.users USING btree (is_active);


--
-- Name: ix_users_is_banned; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_users_is_banned ON public.users USING btree (is_banned);


--
-- Name: ix_users_plan; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_users_plan ON public.users USING btree (plan);


--
-- Name: ix_users_referral_code; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE UNIQUE INDEX ix_users_referral_code ON public.users USING btree (referral_code);


--
-- Name: ix_users_referred_by_id; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_users_referred_by_id ON public.users USING btree (referred_by_id);


--
-- Name: ix_users_telegram_id; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE UNIQUE INDEX ix_users_telegram_id ON public.users USING btree (telegram_id);


--
-- Name: ix_users_username; Type: INDEX; Schema: public; Owner: market_bot
--

CREATE INDEX ix_users_username ON public.users USING btree (username);


--
-- Name: campaigns campaigns_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.campaigns
    ADD CONSTRAINT campaigns_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: channel_ratings channel_ratings_channel_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.channel_ratings
    ADD CONSTRAINT channel_ratings_channel_id_fkey FOREIGN KEY (channel_id) REFERENCES public.telegram_chats(id) ON DELETE CASCADE;


--
-- Name: chat_snapshots chat_snapshots_chat_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.chat_snapshots
    ADD CONSTRAINT chat_snapshots_chat_id_fkey FOREIGN KEY (chat_id) REFERENCES public.telegram_chats(id) ON DELETE CASCADE;


--
-- Name: content_flags content_flags_campaign_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.content_flags
    ADD CONSTRAINT content_flags_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES public.campaigns(id) ON DELETE CASCADE;


--
-- Name: content_flags content_flags_reviewed_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.content_flags
    ADD CONSTRAINT content_flags_reviewed_by_id_fkey FOREIGN KEY (reviewed_by_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: crypto_payments crypto_payments_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.crypto_payments
    ADD CONSTRAINT crypto_payments_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: notifications fk_notifications_user_id; Type: FK CONSTRAINT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT fk_notifications_user_id FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: telegram_chats fk_telegram_chats_owner_user_id; Type: FK CONSTRAINT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.telegram_chats
    ADD CONSTRAINT fk_telegram_chats_owner_user_id FOREIGN KEY (owner_user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: mailing_logs mailing_logs_campaign_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.mailing_logs
    ADD CONSTRAINT mailing_logs_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES public.campaigns(id) ON DELETE CASCADE;


--
-- Name: mailing_logs mailing_logs_chat_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.mailing_logs
    ADD CONSTRAINT mailing_logs_chat_id_fkey FOREIGN KEY (chat_id) REFERENCES public.telegram_chats(id) ON DELETE SET NULL;


--
-- Name: payouts payouts_channel_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.payouts
    ADD CONSTRAINT payouts_channel_id_fkey FOREIGN KEY (channel_id) REFERENCES public.telegram_chats(id) ON DELETE CASCADE;


--
-- Name: payouts payouts_owner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.payouts
    ADD CONSTRAINT payouts_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: payouts payouts_placement_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.payouts
    ADD CONSTRAINT payouts_placement_id_fkey FOREIGN KEY (placement_id) REFERENCES public.mailing_logs(id) ON DELETE CASCADE;


--
-- Name: reviews reviews_channel_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_channel_id_fkey FOREIGN KEY (channel_id) REFERENCES public.telegram_chats(id) ON DELETE SET NULL;


--
-- Name: reviews reviews_placement_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_placement_id_fkey FOREIGN KEY (placement_id) REFERENCES public.mailing_logs(id) ON DELETE CASCADE;


--
-- Name: reviews reviews_reviewee_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_reviewee_id_fkey FOREIGN KEY (reviewee_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: reviews reviews_reviewer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_reviewer_id_fkey FOREIGN KEY (reviewer_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: transactions transactions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: user_badges user_badges_badge_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.user_badges
    ADD CONSTRAINT user_badges_badge_id_fkey FOREIGN KEY (badge_id) REFERENCES public.badges(id) ON DELETE CASCADE;


--
-- Name: user_badges user_badges_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: market_bot
--

ALTER TABLE ONLY public.user_badges
    ADD CONSTRAINT user_badges_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: market_bot
--

REVOKE USAGE ON SCHEMA public FROM PUBLIC;


--
-- PostgreSQL database dump complete
--

\unrestrict b61R6y8cHfqnyj1s55qNqGUCEV6pS11jqZYSi5IOtgCJIYcJfMa0KEqTEs2Xnef

