# SAHARYN AI — Information Security Management System (ISMS)
## ISO 27001:2022 / SOC 2 Type II Alignment Framework
**Document ID:** SEC-POL-001
**Version:** 1.0 (Production Master)
**Status:** Approved for Institutional Deployment
**Classification:** RESTRICTED

---

## 1. Executive Overview
Saharyn AI provides high-fidelity predictive intelligence for mission-critical industrial infrastructure. Given the high-consequence nature of our operations (Oil & Gas, Energy Grids, Mining), security is not an optional feature but the foundational substrate of the platform.

This ISMS Manual outlines the administrative, technical, and physical safeguards implemented to ensure the **Confidentiality, Integrity, and Availability (CIA Triad)** of client data and the SAHARYN causal inference engine.

---

## 2. Information Security Policy (ISO 27001 Clause 5.2)
SAHARYN leadership is committed to:
1.  **Zero-Trust Architecture:** Authenticating every request, every time, regardless of network origin.
2.  **Continuous Compliance:** Utilizing automated auditing and monitoring to detect deviations before they manifest as breaches.
3.  **Data Sovereignty:** Ensuring client telemetry is processed and stored in accordance with local jurisdictional and regulatory requirements.
4.  **Resilience by Design:** Building systems that fail safely and recover autonomously using our own causal inference models.

---

## 3. Organizational Security (ISO 27001 Annex A.5)
### 3.1 Roles and Responsibilities
- **Chief Information Security Officer (CISO):** Ultimate authority for compliance and risk management.
- **Security Engineering Team:** Responsible for the implementation of technical controls (RBAC, Encryption, Network Policies).
- **Incident Response Team:** 24/7 designated personnel for breach containment and recovery.

### 3.2 Human Resources Security
- **Background Checks:** Mandatory for all personnel with access to production data.
- **Security Awareness Training:** Quarterly training on phishing, social engineering, and secure coding practices.
- **Termination Procedures:** Immediate revocation of all access keys, hardware return, and non-disclosure reinforcement.

---

## 4. Asset Management (ISO 27001 Annex A.8)
### 4.1 Inventory of Assets
Saharyn maintains a real-time inventory of all physical and virtual assets, including:
- Cloud-native services (Railway, AWS, Azure).
- Database clusters (TimescaleDB).
- AI Models (XGBoost weights, SHAP configurations).
- Client Service Accounts (NASA, Sentinel Hub, Maximo).

### 4.2 Acceptable Use
All personnel must adhere to the AUP, prohibiting the use of company systems for non-authorized external services or unapproved AI development.

---

## 5. Access Control (ISO 27001 Annex A.9 / SOC 2 CC6)
### 5.1 RBAC Implementation
SAHARYN enforces a Role-Based Access Control system with the following tiers:
- **OBSERVER:** Read-only access to dashboards. No API key creation.
- **OPERATOR:** Can trigger inferences and view logs. No model deployment.
- **ENGINEER:** Can update model weights, modify ETL pipelines, and view audit trails.
- **ADMIN:** Full system authority, including user management and security configuration.

### 5.2 Authentication
- **Multi-Factor Authentication (MFA):** Required for all administrative portals and SSH access.
- **Secret Management:** No credentials stored in plaintext. Use of Environment Variables and Secure Vaults (KMS/Railway Secrets).

---

## 6. Cryptography (ISO 27001 Annex A.10 / SOC 2 CC6.7)
### 6.1 Data at Rest
- **AES-256-GCM:** Used for all database storage volumes and backups.
- **Sovereign Ledger:** Critical audit events are hashed and stored in an immutable ledger (services/compliance/ledger_engine.py).

### 6.2 Data in Transit
- **TLS 1.3:** Mandatory for all API endpoints.
- **Perfect Forward Secrecy (PFS):** Implemented for all session negotiations.
- **mTLS:** Planned for PI Web API and internal microservice communication.

---

## 7. Physical and Environmental Security (Annex A.11)
- SAHARYN leverages Tier 4 Data Centers (via Railway/AWS).
- Biometric access, 24/7 armed security, and environmental controls (FM-200 fire suppression) are outsourced to the cloud provider but verified via SOC 3 reports on an annual basis.

---

## 8. Operational Security (Annex A.12)
### 8.1 Change Management
- No direct pushes to `main`.
- All code changes require 2-peer approval and pass CI/CD linting/testing.
- Emergency changes follow the "Secondary Sign-off" protocol.

### 8.2 Log Management
- **Audit Logs:** Immutable logs stored for 2 years.
- **Centralized Monitoring:** Integration with Datadog/Splunk for real-time anomaly detection.

---

## 9. Communications Security (Annex A.13)
- **Network Segmentation:** Production, Staging, and Development environments are strictly isolated via VLANs/Subnets.
- **Ingress Filtering:** Only ports 443 (HTTPS) and 80 (Redirect only) are open to the public internet.

---

## 10. System Acquisition, Development, and Maintenance (Annex A.14)
- **Secure SDLC:** OWASP Top 10 scanning integrated into the GitHub Actions pipeline.
- **Dependency Management:** Monthly scans for vulnerable packages (`npm audit`, `pip-audit`).

---

## 11. Supplier Relationships (Annex A.15)
- All subcontractors and sub-processors must provide current SOC 2 Type II or ISO 27001 certifications.

---

## 12. Information Security Incident Management (Annex A.16)
(See detailed Incident Response Plan: SEC-PLN-002)

---

## 13. Information Security Aspects of Business Continuity (Annex A.17)
(See detailed Disaster Recovery Plan: SEC-PLN-003)

---

## 14. Compliance (Annex A.18)
- Internal audits conducted bi-annually.
- Policy review conducted annually or upon significant architecture changes.

---
**END OF DOCUMENT**
