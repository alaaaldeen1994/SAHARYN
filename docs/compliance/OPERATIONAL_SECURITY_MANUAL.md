# SAHARYN AI — Operational Security (SecOps) Manual
## Manual ID: SEC-MAN-001
## ISO 27001 / SOC 2 / NIST CSF v2.0 Integrated Framework
**Version:** 3.0 ( المؤسسي - Institutional Calibration)
**Classification:** HIGHLY RESTRICTED - INTERNAL ONLY

---

## 1. Introduction
This manual defines the technical operations and security baseline for the Saharyn platform. It serves as the "Rulebook" for all engineers, SREs, and data scientists. All procedures are audited as part of our SOC 2 Type II evidence collection.

---

## 2. Secure Software Development Life Cycle (S-SDLC)

### 2.1 Governance
All code intended for the SAHARYN production environment must follow the Secure SDLC. This includes:
1.  **Threat Modeling:** Performed during the design phase for any major architecture change (e.g., new satellite API, RBAC overhaul).
2.  **Pull Request (PR) Policy:** 
    - No direct commits to `main` or `release/*` branches.
    - Mandatory review by at least two (2) senior engineers.
    - All CI/CD checks (Lint, Unit, Integration) must pass.
3.  **Secrets Management:** 
    - Hardcoded secrets strictly prohibited.
    - Automated `git-secrets` scan performed on every PR.
    - Use of per-environment Secret Vaults.

### 2.2 Vulnerability Scanning
- **Static Analysis (SAST):** Integrated into GitHub Actions for all Python/JS components.
- **Dynamic Analysis (DAST):** Monthly OWASP ZAP scans against the Staging API.
- **Dependency Scanning:** Automated `Dependabot` or `Snyk` for all third-party libraries.

### 2.3 Deployment (CI/CD)
The deployment pipeline (`.github/workflows/main.yml`) is the only authorized path to production. Manual SSH-based deployments are disabled in the production namespace.

---

## 3. Vulnerability Management Policy

### 3.1 Identification
Vulnerabilities are identified through:
- Automated scanners.
- Internal security audits.
- Bug Bounty program (External researchers).
- Vendor security advisories.

### 3.2 Remediation SLAs (Service Level Agreements)
| Severity | Remediation Time | Board Notification |
| :------- | :--------------- | :----------------- |
| **Critical** | 48 Hours | Immediate |
| **High** | 7 Days | 48 Hours |
| **Medium** | 30 Days | Monthly Report |
| **Low** | 90 Days | Quarterly Report |

### 3.3 Patch Management
- OS-level patches applied within 48 hours of release for production nodes.
- Kubernetes images are rebuilt weekly to include the latest base layers.

---

## 4. Logical Access Control (Deep Logic)

### 4.1 Principle of Least Privilege (PoLP)
Access to production clusters is restricted to the "Break-Glass" SRE team. Developers are granted "Observer" access only to logs and telemetry.

### 4.2 API Integrity
All API calls are protected by:
- **Rate Limiting:** 100 requests per minute per IP for the free tier; 5,000 for enterprise.
- **Payload Validation:** JSON schema validation to prevent SQLi/XSS injection.
- **Audit Logging:** Every successful and failed authenticated request is logged (services/compliance/ledger_engine.py).

### 4.3 Key Rotation
- Production API Keys are rotated every 90 days.
- SSH keys for infrastructure are rotated semi-annually.
- Service Account tokens (NASA, Sentinel Hub) follow vendor-specific rotation policies.

---

## 5. Network Security Architecture

### 5.1 Zero-Trust Micro-segmentation
SAHARYN uses Kubernetes NetworkPolicies to strictly enforce a "Default Deny" posture.
- **Ingress:** Allowed from Load Balancer only.
- **Egress:** Allowed to approved external APIs only (e.g., ladsweb.modaps.eosdis.nasa.gov).
- **Inter-Pod:** `api-gateway` can talk to `timescaledb`, but `etl-worker` cannot.

### 5.2 Encryption in Transit
- **TLS 1.3** is the baseline for all internal and external communication.
- SSL/TLS terminates at the edge (Cloudflare/Load Balancer) and re-encrypts for back-end transmission.

### 5.3 IDS/IPS (Intrusion Detection/Prevention)
- Cloud-native monitoring of anomalous egress traffic.
- Failed authentication spikes trigger immediate IP-level blocking.

---

## 6. Incident Response & Breach Notification (SEC-PLN-002)

### 6.1 Preparation
- 24/7 On-call rotation.
- Pre-defined incident bridges (Slack/Teams).
- Offline "Forensic Snapshots" of all production volumes.

### 6.2 Containment (T + 30 min)
If a breach is confirmed:
- Isolate the affected pods/nodes.
- Revoke all session tokens for the affected user/org.
- Rotate the master JWT secret.

### 6.3 Recovery (T + 2 hours)
- Clean redeploy of the platform from a trusted Git hash.
- Data restoration from the most recent immutable backup.

### 6.4 Notification (Legal/Enterprise)
- **O&G Clients:** Notified within 12 hours of breach confirmation.
- **Regulatory (GDPR/Local Law):** Notified within 72 hours if PII is compromised.

---

## 7. Configuration Management

### 7.1 Infrastructure-as-Code (IaC)
All baseline infrastructure is defined in Terraform and stored in Git. Manual changes to the cloud console (AWS/Azure/Railway) are audited and reverted automatically by the "Drift Detection" engine.

### 7.2 Hardening Standards
- CIS Benchmarks (Center for Internet Security) applied to all Kubernetes clusters.
- All non-essential services/daemons removed from base images.
- Unprivileged users only for container execution.

---

## 8. Physical Security (Third-Party)
As a cloud-native provider, we rely on AWS/Railway for physical security. We verify their compliance annually:
- Biometric entry systems.
- CCTV and 24/7 security patrols.
- Redundant power and cooling systems.

---

## 9. Governance and Audit

### 9.1 Internal Audits
Conducted every 6 months to verify:
- Access logs for anomalous entries.
- Backup restoration success rates.
- Employee training completion.

### 9.2 External Audits (SOC 2 Type II)
The SOC 2 Type II audit window is 6 months (Observation Period). During this time, every Control documented in this manual is tested by independent auditors.

---
**END OF SECOPS MANUAL**
