<div align="center">

# 🌱 Voluntr

**Find meaningful volunteer opportunities. Coordinate volunteers. Recognise every hour given.**

A full-stack community volunteering platform built with Django — connecting volunteers with local causes and giving organizers the tools to recruit, schedule, track attendance and certify contributions.

**[Live demo → voluntr.onrender.com](https://voluntr.onrender.com)**

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-5.2-092E20?logo=django&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon-4169E1?logo=postgresql&logoColor=white)
![Render](https://img.shields.io/badge/Deployed%20on-Render-46E3B7?logo=render&logoColor=white)
![Leaflet](https://img.shields.io/badge/Maps-Leaflet%20%2B%20OSM-199900?logo=leaflet&logoColor=white)
![PWA](https://img.shields.io/badge/PWA-installable-5A0FC8)

</div>

---

## Table of contents

- [Overview](#overview)
- [Features](#features)
  - [For volunteers](#for-volunteers)
  - [For organizers](#for-organizers)
  - [For administrators](#for-administrators)
  - [Platform-wide](#platform-wide)
- [Tech stack](#tech-stack)
- [Project structure](#project-structure)
- [Data model](#data-model)
- [Getting started (local)](#getting-started-local)
- [Configuration](#configuration)
- [Deployment (Render + Neon + Brevo)](#deployment-render--neon--brevo)
- [Management commands](#management-commands)
- [Testing](#testing)
- [Security & privacy](#security--privacy)
- [Sample content](#sample-content)
- [Roadmap](#roadmap)

---

## Overview

Many people want to help but struggle to find a role that fits their skills, location or schedule — and community organizations need a simple way to reach dependable volunteers. **Voluntr** brings both sides together:

- **Volunteers** discover opportunities by cause, city and format, apply in a click, message organizers, check in at events with a QR code, log hours and earn certificates and badges.
- **Organizers** publish listings (reviewed by an administrator), manage applicants, schedule events, approve hours and export records.
- **Administrators** moderate listings, verify organizations and review reports from a branded admin dashboard.

---

## Features

### For volunteers

| Feature | Details |
| --- | --- |
| **Discover opportunities** | Search by keyword, cause, city or format (on-site / remote / hybrid), sort A–Z or newest, paginated results, “no results” guidance and one-click filter reset. |
| **Interactive map** | Leaflet + OpenStreetMap map of in-person and hybrid listings with clickable pins, popups linking to each listing and a cause filter. |
| **Personalised recommendations** | Dashboard suggestions based on the causes, skills and city in your profile. |
| **Bookmarks** | Save opportunities for later and find them on your dashboard. |
| **Applications** | Apply with a short motivation, track status (Pending → Accepted / Rejected), withdraw pending applications, and view a full activity history. Duplicate and closed-listing applications are blocked. |
| **Messaging** | Private chat-style conversation with the organizer for every application, with unread indicators. |
| **Events & calendar** | Monthly calendar with previous/next navigation showing events for opportunities you were accepted to; upcoming and completed activities on the dashboard. |
| **QR attendance** | Scan the organizer’s QR code at the venue to check in (open 30 min before start until 30 min after end; duplicates prevented). |
| **Volunteer hours** | Log hours for accepted roles; organizers approve or reject them. Only approved hours count. |
| **Certificates** | Printable / save-as-PDF certificate of contribution showing approved hours, organization and activity. |
| **Impact & badges** | Personal analytics (hours, applications, check-ins, hours by cause) and five achievement badges from *First steps* (1 h) to *Century of service* (100 h). |
| **Profile** | Name, bio, city, skills and causes you care about, with validation. Guided “Finish setting up” checklist. |
| **Notifications** | In-app updates (application decisions, new events, messages, approved hours) with an unread counter, open-to-read and “mark all as read”. Key updates are also emailed. |

### For organizers

| Feature | Details |
| --- | --- |
| **Organizer dashboard** | Listings, applications received, items awaiting review and approved volunteer hours at a glance. |
| **Create & edit listings** | Title, cause, city, format, summary, description, skills, commitment, capacity and deadline. New listings go to an administrator for approval. |
| **Close / reopen listings** | Stop new applications without deleting the listing. |
| **Applicant review** | Read motivations, accept (capacity-aware) or reject, and message applicants. Volunteers are notified by email and in-app. |
| **Events** | Create, edit and cancel events per listing; accepted volunteers are notified automatically. |
| **Attendance QR** | Auto-generated, printable check-in QR code per event with a live attendance list. |
| **Hours approval** | Approve or reject submitted hours in a review table. |
| **Map location** | Set an exact public meeting point for a listing (defaults to the city centre). |
| **Organization profile** | Public profile with bio, city, website and listings; verification by administrators. |
| **CSV export** | Download all applications (name, email, status, date) with spreadsheet-injection protection. |
| **Organization analytics** | Hours by cause, total applications, acceptances and unique volunteers. |

### For administrators

- **Branded admin dashboard** with live stats (users, live listings, applications, approved hours) and a **“Needs attention”** panel for listings awaiting approval, open reports and organizations to verify.
- **Moderation queue** — approve & publish listings in bulk (organizers are notified automatically), unpublish, or mark reports resolved.
- **Organization verification** actions, plus full management of users, applications, hours, events, articles, contact messages, newsletter subscribers and reports.
- Private messages are intentionally **not** exposed in the admin.

### Platform-wide

- **Accounts** — username/password registration with role selection (Volunteer or Organizer), strong password validation, duplicate email/username checks.
- **Google sign-in** — OAuth 2.0 with PKCE, state and nonce checks; real names are imported and existing password accounts are never silently linked.
- **Email verification** — required before applying, posting or messaging (configurable); resend with rate limiting; change-email flow.
- **Password recovery** — single-use reset links via email.
- **Login protection** — rate limiting after repeated failed sign-ins.
- **Transactional email** — Brevo HTTPS API backend (works on hosts that block SMTP), with SMTP and console fallbacks.
- **Organizations directory** — searchable, filterable by city, with cover images, verification badges and linked listings.
- **Journal** — articles with search, topic filter, related stories and share buttons.
- **Contact form, newsletter sign-up** (duplicate-safe) and **listing reports**.
- **Dark mode** — remembered per device, applied before page paint.
- **Responsive design** — mobile navigation, horizontally scrollable tables, layouts tested at phone, tablet and desktop widths.
- **PWA** — web app manifest, service worker and offline page (private pages are never cached).
- **SEO** — per-page titles and descriptions, Open Graph / Twitter tags, canonical URLs, `sitemap.xml` and `robots.txt`.
- **Public JSON API** — read-only `/api/opportunities/`.
- **Health check** — `/health/` for uptime monitoring.
- **Custom 404 / 500 pages.**

---

## Tech stack

| Layer | Technology |
| --- | --- |
| Backend | Python 3.12, Django 5.2 |
| Database | PostgreSQL (Neon) in production, SQLite locally — via `dj-database-url` |
| Frontend | Django templates, hand-written CSS (light & dark themes), vanilla JavaScript |
| Maps | Leaflet 1.9 + OpenStreetMap tiles |
| Auth | Django auth, Google OAuth 2.0 (`google-auth`) |
| Email | Brevo transactional API (custom Django email backend) / SMTP |
| QR codes | `qrcode` + Pillow |
| Static files | WhiteNoise (compressed, hashed) |
| Server | Gunicorn on Render |
| Containers | Dockerfile included |

---

## Project structure

```
├── config/                 # Settings, root URLs, WSGI
├── core/                   # Opportunities, applications, hours, profiles, journal, admin
│   ├── management/commands/seed_demo.py
│   ├── templatetags/       # Image helpers, icons, admin dashboard stats
│   ├── tests.py            # Core workflow tests
│   └── test_checklist.py   # End-to-end walkthrough of the QA checklist
├── community/              # Organizations, map, events, QR check-in, messaging,
│   │                       # notifications, Google sign-in, email verification
│   ├── email_backend.py    # Brevo HTTPS email backend
│   └── management/commands/send_event_reminders.py
├── templates/              # Site, dashboard, auth, community and admin templates
├── static/                 # CSS, JS, images, favicon and PWA icons
├── render.yaml             # Render blueprint
└── Dockerfile
```

---

## Data model

```
User ─┬─ Profile (role, city, skills, interests, bio)
      ├─ Account (verified email, Google subject)
      ├─ Organization (public profile, verification)
      ├─ Opportunity (owner) ─┬─ Location (map pin)
      │                       ├─ Event ─┬─ Attendance
      │                       │         └─ Reminder
      │                       └─ Application ─┬─ Hours
      │                                       └─ Message
      ├─ Bookmark, Notification, ListingReport
Article · Contact · Subscriber · LoginAttempt
```

---

## Getting started (local)

**Prerequisites:** Python 3.12+ and Git.

```bash
git clone https://github.com/chandana-galgali/voluntr.git
cd voluntr

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
python manage.py migrate          # also creates the sample content
python manage.py createsuperuser
python manage.py runserver
```

Open **http://127.0.0.1:8000** (admin at `/admin/`).

Locally, `DEBUG` is on by default, SQLite is used, and emails (verification, password reset) are printed to the terminal — copy links from there.

---

## Configuration

All configuration is via environment variables.

| Variable | Required | Purpose |
| --- | --- | --- |
| `SECRET_KEY` | Production | Django secret key. |
| `DEBUG` | — | `1` locally (default), `0` in production. |
| `DATABASE_URL` | Production | PostgreSQL connection string (e.g. Neon). Defaults to SQLite. |
| `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` | — | Extra hosts; the Render hostname is added automatically. |
| `PUBLIC_BASE_URL` | Recommended | e.g. `https://voluntr.onrender.com` — used for links in emails. |
| `BREVO_API_KEY` | Recommended | Brevo **API** key (`xkeysib-…`). Sends email over HTTPS. |
| `DEFAULT_FROM_EMAIL` | Recommended | e.g. `Voluntr <hello@yourdomain.com>` — must be a verified Brevo sender. |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | — | SMTP fallback if `BREVO_API_KEY` is not set. |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | Optional | Enables “Continue with Google”. |
| `GOOGLE_REDIRECT_URI` | Optional | `https://<your-domain>/community/google/callback/` |
| `REQUIRE_EMAIL_VERIFICATION` | — | Default `1`. Set `0` to let unverified users act (e.g. while setting up email). |
| `SEED_DEMO_ON_MIGRATE` | — | Default `1`. Creates sample listings, articles and organizations after `migrate` (create-only). |

---

## Deployment (Render + Neon + Brevo)

1. **Neon** — create a PostgreSQL project and copy the connection string.
2. **Brevo** — create an API key, verify a sender address, and disable *Authorised IPs* blocking (Render’s IPs change).
3. **Google Cloud (optional)** — create an OAuth client; add `https://<your-domain>/community/google/callback/` as a redirect URI.
4. **Render** — create a Python web service from this repo:
   - **Build command:** `pip install -r requirements.txt && python manage.py collectstatic --noinput`
   - **Start command:** `python manage.py migrate && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`
   - **Health check path:** `/health/`
   - Add the environment variables above (`DEBUG=0`).
5. **Reminders (optional)** — add a Render Cron Job running `python manage.py send_event_reminders` hourly.

A `render.yaml` blueprint and a `Dockerfile` are included.

---

## Management commands

| Command | Purpose |
| --- | --- |
| `python manage.py seed_demo` | Create missing sample listings, journal articles and organizations. Never overwrites edits. |
| `python manage.py seed_demo --refresh` | Reset sample content to the bundled versions. |
| `python manage.py send_event_reminders` | Notify and email accepted volunteers about events in the next 24 hours (idempotent), and clean up expired login-attempt records. |

---

## Testing

```bash
python manage.py test
```

The suite (38 tests) covers registration and validation, login and rate limiting, Google sign-in, email verification and password reset, the Brevo backend, profiles, search and filters, bookmarks, the full application lifecycle, organizer tools, organizations, the map, events and QR check-in, hours and certificates, badges and analytics, notifications, messaging, reminders, journal, contact/newsletter/reports, SEO/PWA endpoints, the admin and access control. `core/test_checklist.py` mirrors the project’s manual QA checklist.

---

## Security & privacy

- HTTPS redirect, HSTS, secure cookies and `X-Content-Type-Options` in production.
- Role- and ownership-based access on every private view (applications, messages, events, certificates, exports); POST-only state changes with CSRF protection.
- Login rate limiting; signed, expiring email-verification tokens; single-use password reset links.
- Google OAuth with PKCE, state and nonce verification.
- `Cache-Control: private, no-store` and `noindex` on authenticated pages; the service worker never caches private content.
- CSV exports are protected against formula injection; user content is HTML-escaped.
- Map pins use public meeting points or approximate city centres — never private addresses.
- Secrets are read from environment variables only.

---

## Sample content

To make the demo explorable, Voluntr ships with **18 sample opportunities**, **8 journal articles** and **9 sample organizations**. They are clearly labelled *Demo listing* / *Sample profile*, are not verified, and do not represent real events or registered organizations. Sample organization accounts are inactive and cannot sign in. Photography consists of AI-generated illustrative scenes.

---

## Roadmap

- Automatic event reminders via a scheduled job
- Organization logo and cover uploads
- Skill-based matching scores and saved searches
- Multi-language support

---

<div align="center">

Built with 💚 by Chandana Galgali for volunteers and the communities they serve · **[voluntr.onrender.com](https://voluntr.onrender.com)**

</div>
