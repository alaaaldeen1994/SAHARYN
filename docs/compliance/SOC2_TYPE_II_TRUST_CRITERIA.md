# SAHARYN AI — SOC 2 Type II Compliance Framework
## Trust Services Criteria (TSC) Mapping & Controls Manual
**Document ID:** SEC-SOC-002
**Version:** 2.1 (Production/Institutional)
**Reference:** AICPA TSP Section 100
**Security / Confidentiality / Availability Focus**

---

## 1. Introduction
This document maps SAHARYN's technical and administrative controls directly to the AICPA SOC 2 Common Criteria (CC). This is the primary reference for third-party auditors and enterprise security teams (e.g., Aramco, Chevron, Shell).

---

## 2. Common Criteria (CC) - Security (Primary)

### CC 1.0 Control Environment
**CC 1.1 - Commitment to Integrity and Ethics**
- **Control:** Corporate Code of Conduct signed by all employees. Continuous vetting of personnel.
- **Evidence:** Employee handbooks and signed onboarding checklists.

**CC 1.2 - Oversight and Board Independence**
- **Control:** CISO reports directly to the Board of Directors, independent of the CTO/Lead Developer.
- **Evidence:** Quarterly security board minutes.

### CC 2.0 Communication and Information
**CC 2.1 - Internal Communications**
- **Control:** Integrated Slack/Teams channels for automated security alerts and breach notifications.
- **Evidence:** Real-time alert logs from CI/CD and Kubernetes.

**CC 2.2 - External Communications**
- **Control:** Published Security Portal ([saharyn.com/security](https://saharyn.com/security)) for breach reporting and trust documentation.
- **Evidence:** Presence of public-facing security policy links.

### CC 3.0 Risk Assessment
**CC 3.1 - Risk Identification**
- **Control:** Semi-annual formal risk assessment covering cloud assets, AI model integrity, and data leakage.
- **Evidence:** Risk register (SEC-RISK-001) with prioritized mitigation plans.

**CC 3.2 - Fraud Identification**
- **Control:** AI-driven anomaly detection on API access patterns and billing spikes.
- **Evidence:** Audit log analysis for non-standard traffic patterns.

### CC 4.0 Monitoring Activities
**CC 4.1 - Ongoing and Separate Evaluations**
- **Control:** Annual external penetration testing by certified CREST/OSCP entities.
- **Evidence:** Pen-test summary reports (Redacted for external use).

**CC 4.2 - Corrective Action Management**
- **Control:** Formal "Remediation SLAs" for vulnerabilities (Critical: 48h, High: 7 days, Medium: 30 days).
- **Evidence:** Bug-tracker (Jira/GitHub) tickets linked to CVE scans.

### CC 5.0 Control Activities
**CC 5.1 - Selection and Development of Controls**
- **Control:** Adoption of NIST 800-53 security controls for all federal and high-consequence contracts.
- **Evidence:** This mapping document.

---

## 3. Logical Access & System Security (CC 6.0)

### CC 6.1 - Access Rights Management
- **Description:** Authorization to systems is restricted based on role and need-to-know.
- **Implementation:**
  - `rbac.py`: Core logic for permission enforcement.
  - `verify_enterprise_access`: Middleware for API-key and session validation in `main.py`.
- **Evidence:** List of current users and their assigned roles (Admin, Engineer, Operator).

### CC 6.2 - User Access Revocation
- **Description:** Offboarding procedures ensure immediate removal of access.
- **Implementation:** Centralized OIDC (Okta/Auth0) for dashboard and CLI.
- **Evidence:** Revocation logs in the identity provider.

### CC 6.6 - Boundary Protection (WAF/Firewall)
- **Description:** External threats are mitigated via network boundaries.
- **Implementation:**
  - Cloudflare WAF for `saharyn.com`.
  - Kubernetes NetworkPolicies in `/infrastructure/k8s/` restricting Pod-to-Pod communication.
- **Evidence:** K8s YAML manifests showing zero-trust inter-service policies.

---

## 4. System Operations (CC 7.0)

### CC 7.1 - Detection of Operational Anomaly
- **Description:** Real-time visibility into system health.
- **Implementation:** 
  - `/v2/system/health`: Automated health-check API.
  - Prometheus/Grafana: Scada and AI performance monitoring.
- **Evidence:** Dashboard uptime logs (Prometheus snapshots).

### CC 7.2 - Incident Response
- **Description:** Formal protocol for breach containment.
- **Implementation:** See SEC-PLN-002 (Incident Response Plan).
- **Evidence:** Past incident post-mortems (if any).

---

## 5. Change Management (CC 8.0)

### CC 8.1 - SDLC Controls
- **Description:** All code changes are validated and approved.
- **Implementation:** 
  - GitHub PR (Pull Request) required for all merges.
  - Mandatory 2-person code review.
  - Automated tests must pass 100%.
- **Evidence:** Git commit history and PR approval logs.

---

## 6. Risk Mitigation (CC 9.0)

### CC 9.1 - Business Continuity & Resilience
- **Description:** Operations can continue despite infrastructure failure.
- **Implementation:** 
  - Multi-AZ (Availability Zone) deployment in Railway/AWS.
  - Snapshotting of PostgreSQL/TimescaleDB every 6 hours.
- **Evidence:** Backup schedules and successful restoration test logs.

---

## 7. Confidentiality (Criteria Section C1)

### C1.1 - Data Classification
- **Control:** Data is tagged as Public, Internal, Restricted, or Highly Sensitive (PII/PHI).
- **Implementation:** Database schemas include sensitivity flags.

### C1.2 - Disposal of Confidential Information
- **Control:** Secure deletion of data upon client request or contract termination.
- **Implementation:** Overwriting storage sectors and certificate revocation.

---

## 8. Availability (Criteria Section A1)

### A1.1 - Capacity Management
- **Control:** Scaling strategies for handling industrial-scale telemetry.
- **Implementation:** Kubernetes Horizontal Pod Autoscaler (HPA) configured for CPU/Memory triggers.
- **Evidence:** HPA configuration in `k8s/api-deployment.yaml`.

### A1.2 - Environmental Protection
- **Control:** Mitigation of non-logical threats (Fire, Power, Flood).
- **Implementation:** Leveraging Tier 4 cloud infrastructure providers.

---
**END OF SOC 2 TYPE II MAPPING**
