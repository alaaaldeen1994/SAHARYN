# 📋 SAHARYN AI: Investor Demonstration Playbook
**Version 2.1.0** | **Operational Readiness: CERTIFIED**

This playbook outlines the standard sequence for live investor and partner walkthroughs. It is designed to showcase the platform's ability to model complex causal physics, predict industrial failure, and generate verifiable ROI.

---

## 1. System Startup & Health Verification
**Goal**: Demonstrate that the system is operational and self-monitoring.

1.  **Launch the Dashboard**: Open the SAHARYN Mission Control interface.
2.  **Verify LIVE Connectivity**:
    *   Point to the **AI_CORE: ONLINE** indicator in the header.
    *   Show the **System Health Status** (Top Left) confirmed as `OPERATIONAL`.
    *   *Technical Detail*: Mention the `/v2/system/health` endpoint, which performs real-time SQL pings and spectral link validations to ensure the entire industrial tech stack is healthy.

## 2. Stability Lock Activation
**Goal**: Ensure a controlled narrative environment.

1.  **Explain the Lock**: Inform the audience that the platform is currently connected to real-time Copernicus (ESA) and MODIS (NASA) satellite feeds.
2.  **Activate Mode**: Click the **STABILITY_LOCKED** (Anchor Icon) button in the header.
3.  **Visual Confirmation**: The label will change to **STABILITY_LOCKED: ON** (Green).
4.  **Value Prop**: Explain that this "freezes" the ingested telemetry at a nominal state. This prevents sudden atmospheric jumps (like a real-time storm elsewhere in the region) from interrupting the demonstration logic.

## 3. Baseline Operation (The "Nominal" State)
**Goal**: Establish a reference for "Normal" conditions.

1.  **Environmental View**: Observe the **Aerosol Optical Depth (AOD)** slider at ~0.12 and **Wind Speed** at <5 m/s.
2.  **Asset Health**:
    *   Show the **Asset Stress Map**. All assets (Pumps, Rotors) should be **Green**.
    *   Point to the **Reliability Index**: Should be at **~98-99%**.
3.  **ML Performance**: Highlight the **MLOps Drift Status** as `STABLE`. This proves the AI model is operating within its training distribution.

## 4. Scenario Demonstration: The Sandstorm Cascade
**Goal**: Show the full causal chain from environment to mechanical failure.

1.  **Trigger Scenario**: In the **DEMO_ORCHESTRATOR** strip, click the **SANDSTORM** button.
2.  **Walkthrough the Causal Chain**:
    *   **I. Atmospheric Event**: The **AOD** jumps to **0.95**. Observe the map background shifting to a hazy amber.
    *   **II. Filter Stress**: Point to the **Deep Chemical Diagnostics** panel. **Kinetic Abrasion** and **Dust Deposition (DSI)** will begin to climb.
    *   **III. Secondary Effects**: Explain that dust is occluding intake filters, causing intake pressure to drop.
    *   **IV. Mechanical Anomaly**: Observe the **Rotor Vibration** metrics shifting from 1.2 mm/s to **~7.5 mm/s**.
    *   **V. Asset Degradation**: The **Reliability Index** drops, and the Asset Stress Map turns **Red** (Critical).

## 5. AI Recommendation & ROI Analysis
**Goal**: Demonstrate the financial value of the intervention.

1.  **Review the Action Card**: A recommendation (e.g., `EMERGENCY SHUTDOWN` or `FLUSH FILTRATION`) will appear.
2.  **Analysis Checklist**:
    *   **Predicted Failure Window**: Highlight that the AI detected the failure **48 hours** before a mechanical catastrophe would occur.
    *   **Root Cause Trace**: Expand the trace to show the logic: `AOD ↑ → DSI ↑ → P_Diff ↓ → VIB ↑`.
    *   **Avoided Loss**: Show the estimate (typically **$1.5M+**). Explain that this includes the **$320k** replacement cost + **14 hours** of lost production.
    *   **ROI Multiple**: Highlight the **40x+ ROI** for the recommended intervention cost.

## 6. System Recovery
**Goal**: Show rapid reset capabilities.

1.  **Reset Command**: Click the **RESET** button on the mission strip.
2.  **Visual Feedback**:
    *   Watch the **AOD** return to **0.08**.
    *   The **Asset Stress Map** reverts to **Green** instantly.
3.  **Conclusion**: Explain that SAHARYN has "cleared" the incident and is once again monitoring for the next anomaly, proving that the system requires zero manual maintenance to maintain its predictive readiness.

---

> [!TIP]
> **Key Talking Point**: "SAHARYN doesn't just watch for vibrations; it understands the *why* by linking the atmospheric physics of the desert directly to the mechanical reliability of your most critical assets."
