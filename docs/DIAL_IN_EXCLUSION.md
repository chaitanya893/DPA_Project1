# Telephone Dial-In Audio Capture: Out of Scope Justification

*Project: Earnings Call Capture and Transcription Pipeline (Assignment 1)*  
*Phase 2 Compliance Documentation*

---

## 1. Executive Rationale

As specified in the assignment brief, **telephone dial-in capture is deliberately out of scope**. The pipeline captures earnings audio exclusively via digital webcast streams (HLS/progressive MP3/MP4) and archived web replays. The decision to exclude PSTN telephone dial-in is grounded in three decisive barriers:

### A. Legal & Compliance Risks
- **Two-Party Consent & Wiretapping Laws**: Earnings call dial-in bridges span multiple legal jurisdictions across the US (e.g., California, Florida, Massachusetts requiring all-party consent) and Canada (Criminal Code Section 184). Automated algorithmic dialers connecting to PSTN conference bridges without explicit operator authorization and audible disclosure introduce legal liabilities regarding non-consensual call interception.
- **Operator Verification Barriers**: Dial-in lines frequently require live human operator validation (providing name, institution, and participant passcode), which cannot be automated reliably under zero-credential and non-evasion compliance rules.

### B. Prohibitive Financial & Infrastructure Costs
- **SIP Trunking & Telephony Bridge Fees**: Running automated parallel dialers across 25 to 500 companies requires dedicated SIP trunks, Twilio/Plivo telephony API minutes, and toll-free inbound/outbound per-minute billing (~$0.02 to $0.05/minute per channel). Over hundreds of hour-long quarterly calls, telephony transport costs exceed web stream scraping by over 100x.
- **Hardware Dialing Infrastructure**: Telephony requires maintaining dedicated Asterisk/FreePBX gateways with carrier-grade trunk redundancy.

### C. Technical & Audio Quality Degradation (ASR Impact)
- **Narrowband Codec Limitations (G.711 / 8 kHz)**: Traditional PSTN telephone audio is band-limited to 300 Hz – 3,400 Hz sampled at **8 kHz**. In contrast, modern ASR models (e.g., Whisper, Conformer, NeMo) require wideband audio sampled at **16 kHz** to resolve phonetic nuances, high-frequency consonants (e.g., 's', 'f', 'th'), and financial jargon (e.g., "EBITDA", "basis points").
- **Signal-to-Noise Ratio (SNR)**: PSTN networks introduce packet loss, line echo, and companding noise (μ-law/A-law), which degrades Word Error Rate (WER) by 15% to 30% compared to digital 16 kHz MP3/HLS webcasts.
