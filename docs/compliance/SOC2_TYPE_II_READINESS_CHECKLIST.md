# SAHARYN AI — SOC 2 Type II Readiness Checklist
## Document ID: SEC-RDY-001
## Implementation Roadmap: 6-Month Observation Window
**Version:** 1.0 (Audit-Mode Ready)
**Classification:** RESTRICTED

---

## 1. Phase 1: Preparation and Scoping (Month 1)
The first 30 days are dedicated to defining the audit boundary and identifying the Trust Services Criteria (TSC) to be audited.

- [x] **Define the Audit Boundary:** SaaS Platform (`api.saharyn.com`), Cloud SQL Instance, MLflow Registry.
- [x] **Identify the TSCs:** Security (Common Criteria), Confidentiality, and Availability.
- [x] **Appoint the Audit Team:** CISO (Internal) + External CPA Firm (TBD).
- [x] **Perform Initial Gap Analysis:** Comparison of current architecture against AICPA TSC v2.0.

---

## 2. Phase 2: Technical Control Implementation (Months 2-3)
This phase addresses specific architectural gaps identified in Phase 1.

### 2.1 Identity and Access Management (IAM)
- [x] **RBAC Audit:** Ensure all users have "Least Privilege" access.
- [ ] **MFA Enforcement:** Verify MFA is required for all administrative access (Railway, AWS, GitHub).
- [x] **Credential Rotation:** Standardized 90-day rotation of all service account keys.
- [ ] **JIT Access:** Implementation of "Just-In-Time" (JIT) production access for SREs.

### 2.2 Data Protection & Encryption
- [x] **Encryption at Rest:** Verify AES-256 for all production databases and backups.
- [x] **Encryption in Transit:** Enforce TLS 1.3 for all public and private endpoints.
- [x] **Data Siloing:** Verify logical isolation of client-specific telemetry.

### 2.3 Network Security
- [x] **WAF Configuration:** Cloudflare WAF active with OWASP Core Rule Set (CRS).
- [x] **Kubernetes NetworkPolicies:** Zero-trust micro-segmentation active.
- [x] **External Scans:** Monthly DAST (ZAP) scheduled and logging.

---

## 3. Phase 3: Administrative and Policy Framework (Month 4)
Policies are formalized and socialized with the organization.

- [x] **Master ISMS Manual:** SEC-POL-001 finalized.
- [x] **Disaster Recovery (DR) Plan:** SEC-PLN-003 finalized.
- [x] **Incident Response Plan:** SEC-PLN-002 finalized.
- [x] **Employee Training:** Secure Coding and PHI/PII awareness course mandatory.
- [x] **Background Checks:** All production-access staff vetted.

---

## 4. Phase 4: Evidence Collection and Monitoring (Months 5-6)
The "Type II" observation period begins. Controls must be consistently applied for at least 6 months.

- [ ] **Automated Evidence Capture:** Use of Vanta, Drata, or Tugboat Logic for evidence collection.
- [ ] **Continuous Compliance:** Real-time monitoring of PR approvals and MFA status.
- [ ] **Internal Audit:** Perform a "Mock Audit" to simulate CPA questions.
- [ ] **External Audit Kick-off:** CPA Firm begins fieldwork for the final report.

---

## 5. SOC 2 Common Criteria Checklist (Deep Dive)

### CC 1: Control Environment
- [x] **CC 1.1:** Integrity and Ethics (Code of Conduct + Sign-off).
- [x] **CC 1.2:** Oversight (CISO reporting to Board).
- [x] **CC 1.3:** Organizational Structure (Clear reporting lines in Org Chart).

### CC 6: Logical Access
- [x] **CC 6.1:** Access Management (RBAC logic verified).
- [x] **CC 6.2:** External Access (Enterprise API keys).
- [x] **CC 6.6:** Boundary Protection (Ingress/Egress filtering).
- [x] **CC 6.7:** Cryptography (AES-256 / TLS 1.3 implementation).

### CC 7: System Operations
- [x] **CC 7.1:** Anomaly Detection (Prometheus + Health APIs).
- [x] **CC 7.2:** Incident Response (Protocol established).

---

## 6. Known Gaps & Remediation Status
As of Month 1, the following items are still "In-Progress" for full SOC 2 Type II compliance:

| Gap | Severity | Status | Due Date |
| :--- | :------- | :----- | :------- |
| **MFA for Local Dev** | Medium | In-Progress | Month 2 |
| **SOC 3 Report from Railway**| High | Pending Request | Month 1 |
| **DR Restore Drill** | High | Scheduled | Month 3 |
| **Vendor Assessment v2** | Medium | Draft Phase | Month 4 |

---
**END OF SOC 2 READINESS CHECKLIST**
