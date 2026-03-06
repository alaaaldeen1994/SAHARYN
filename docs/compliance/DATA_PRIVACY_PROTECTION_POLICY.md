# SAHARYN AI — Data Privacy and Protection Policy
## Document ID: PRIV-POL-001
## Standards: KSA PDPL, EU GDPR, UAE PDPL Alignment
**Version:** 1.8 (المملكة العربية السعودية / الدولي - KSA/International)
**Classification:** RESTRICTED

---

## 1. Introduction
This policy defines the lifecycle of all data ingested, processed, and stored by the Saharyn AI platform. We prioritize **Data Sovereignty** and **Personal Data Privacy** as per the Saudi Personal Data Protection Law (PDPL) and the EU General Data Protection Regulation (GDPR).

---

## 2. Scope and Application
This policy applies to all systems and personnel with access to:
1.  **Client Telemetry:** Industrial SCADA, Sensor maps.
2.  **User Data:** Employee names, emails, API keys.
3.  **Geospatial Data:** Site coordinates, Satellite imagery.
4.  **Audit Logs:** System and user activity records.

---

## 3. Data Classification Tiering

| Tier | Classification | Sensitivity | Handling Requirements |
| :--- | :------------- | :---------- | :-------------------- |
| **0** | **PUBLIC** | Low | No encryption required (e.g., General MODIS data). |
| **1** | **INTERNAL** | Medium | AES-256 for storage; TLS for transit. |
| **2** | **RESTRICTED** | High | PII, Credentials, Asset performance logs. MFA required. |
| **3** | **HIGHLY SENSITIVE** | Critical | Strategic site coordinates, High-consequence models. JIT access. |

---

## 4. Personal Data Protection (KSA PDPL / GDPR)

### 4.1 Legal Basis for Processing
SAHARYN processes personal data only under the following conditions:
- **Contractual Necessity:** To provide the AI services requested.
- **Legal Obligation:** To comply with national security/industrial regulations.
- **Legitimate Interest:** To improve system security and prevent fraud.

### 4.2 Data Subject Rights (DSR)
All data subjects (users) are entitled to:
- **Right to Access:** Receive a copy of all personal data held by SAHARYN.
- **Right to Erasure ("Right to be Forgotten"):** Request deletion of their account and associated metadata.
- **Right to Rectification:** Update incorrect profile information.
- **Right to Portability:** Export their data into a machine-readable format.

### 4.3 Data Protection Officer (DPO)
A designated DPO oversees all privacy impact assessments (PIA) and ensures compliance with the Saudi Data & AI Authority (SDAIA).

---

## 5. Technical Safeguards (The "Hardened" Layer)

### 5.1 Encryption Standards
- **At Rest:** Advanced Encryption Standard (AES) with a 256-bit key (AES-256-GCM).
- **In Transit:** Transport Layer Security (TLS) version 1.3 only. 1.2 is deprecated.
- **Key Management:** Rotation of master encryption keys every 180 days.

### 5.2 Data Siloing
- Multi-tenancy is enforced at the database layer (Schema-level or Instance-level).
- Client A's data is never processed by workers assigned to Client B.

### 5.3 Anonymization and Pseudonymization
- All model training uses pseudonymized telemetry.
- Mapping between `asset_id` and physical location is stored in a separate, encrypted vault.

---

## 6. Data Retention and Disposal

### 6.1 Retention Schedule
| Data Type | Retention Period | Rationale |
| :-------- | :--------------- | :-------- |
| **Inference Logs** | 2 Years | Model performance auditing. |
| **Audit/Security Logs** | 5 Years | Regulatory requirement for SOC 2 / ISO 27001. |
| **User Account Data** | Contract Duration + 1 Year | Operational continuity. |
| **Satellite Metadata** | 10 Years | Climatological trending analysis. |

### 6.2 Secure Disposal
Upon decommissioning of a client or asset:
- **Software Wipe:** All database rows are logically or physically deleted.
- **Certificate Revocation:** All associated client API keys are invalidated immediately.
- **Backups:** Purged within 90 days following the primary deletion.

---

## 7. Cross-Border Data Transfer
- **KSA Focus:** For Saudi Arabian operations, all "High-Sensitivity" data remains within the Kingdom as per SDAIA regulations unless explicit permission is granted for external processing.
- **EU Focus:** Standard Contractual Clauses (SCCs) are used for transfers involving European data subjects.

---

## 8. Data Breach Protocol
In the event of a privacy breach:
1.  **Detection:** Triggered by DLP (Data Loss Prevention) software or anomaly detection.
2.  **Notification:** Affected users and regulatory bodies notified within 72 hours.
3.  **Remediation:** Full post-mortem and logic hardening to prevent recurrence.

---
**END OF DATA PRIVACY POLICY**
