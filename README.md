# 🌱 Grow Fasal - Intelligent Farm Management

**Grow Fasal** is a comprehensive, full-stack agricultural advisory system tailored for modern farmers. It transitions beyond simple short-term weather forecasting by providing long-term, structurally advanced climatic intelligence, localized accessibility, and proactive alerts.

---

## 🚀 Features Implemented to Date

### 1. Core Intelligence & Climatology Engine
*   **Modular AI Engine**: Built the `ClimatologyEngine`, a core heuristic system capable of interpreting geolocation, cross-referencing it with seasonal Indian cycles (Rabi, Kharif, Zaid), and outputting long-term intelligent data.
*   **6-Month Forecasting & Crop Suitability**: Recommends what crops to plant currently based on exact geography, and helps farmers plan land preparation for the upcoming seasons.
*   **Actionable Advisory**: Generates highly structured reports detailing predictive Irrigation Strategies, Pesticide/Sowing Windows, and General Crop Care.

### 2. Full-Stack Database & Authentication
*   **Prisma ORM & SQLite**: Completely designed the database architecture (`schema.prisma`) mapping `Users`, `FarmProfiles`, and `Reports` for offline-ready, scalable local development.
*   **NextAuth.js Integration**: Built a secure authentication portal (`/login`) enabling farmers to securely log into the system using their Phone Numbers.

### 3. Farmer Dashboard & Historical Tracking
*   **Protected Dashboard**: Created a secure `/dashboard` route accessible only to authenticated farmers.
*   **Farm Profile Persistence**: Farmers can track their exact farm location, total acreage, current planted crops, and unique soil types continuously.
*   **Cloud Report Saving**: Once a farmer generates an AI intelligence report, it is permanently saved to the SQLite database. The dashboard tracks the completely historical archive of all previously generated advice.

### 4. Immense Localization (22 Indian Languages)
*   **Universal i18n Dictionary**: Built a custom translation `LanguageContext` containing exactly mapped interface strings for all **22 Scheduled Official Languages of India**, including:
    *   *English, Hindi, Bengali, Telugu, Marathi, Tamil, Urdu, Gujarati, Kannada, Odia, Malayalam, Punjabi, Assamese, Maithili, Sanskrit, Nepali, Konkani, Manipuri, Bodo, Dogri, Santhali, and Kashmiri.*
*   **Instant UI Toggle**: A globally available dropdown allows seamless, instant translation of the entire web application without breaking complex React Router state.

### 5. Native Accessibility (Voice & Audio)
*   **Voice Dictation (Speech-to-Text)**: Replaced standard typing requirements with a Microphone button. Utilizing the browser's Native Web Speech API, farmers can simply speak the name of their village/city. The engine automatically maps the recognition language to their selected dialect (e.g., `mr-IN` for Marathi).
*   **Read Aloud (Text-to-Speech)**: Addressing literacy barriers by adding a "Read Aloud" button directly to the complex farming reports. The application constructs a localized narrative of the 6-month forecast and verbally narrates it to the farmer.

### 6. Proactive Twilio SMS Alerts
*   **Automated Microservices**: Engineered a reliable `/api/alerts` backend route powered by the Twilio Node.js SDK.
*   **Severe Weather Push**: Capable of directly texting farmers' mobile devices if extreme weather (heavy rain, sudden frost) is imminent, advising them to delay pesticide use or alter irrigation.
*   **Simulated Testing Base**: Deployed a safe fallback system and a "Send Test Alert" mechanism inside the Dashboard. If Twilio credentials are not actively provided in the `.env.local`, the server safely captures and logs the simulated SMS payload, allowing perfect local testing.

---

## 🛠 Tech Stack
*   **Frontend**: Next.js 14 (App Router), React, Vanilla CSS (Glassmorphism UI)
*   **Backend**: Next.js Node.js API Routes, NextAuth.js
*   **Database**: SQLite via Prisma ORM
*   **Integrations**: Twilio SDK (SMS Alerts), Web Speech API (Voice/Audio)
