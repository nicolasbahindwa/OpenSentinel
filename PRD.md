
---

# Product Requirements Document: OpenSentinel
## AI Planning & Automation Agent (OpenClaw-Compliant Architecture)

**Version:** 2.0  
**Status:** Draft for Stakeholder Review  
**Classification:** Internal Use  
**Last Updated:** 2026-02-21

---

## 1. Executive Summary

OpenSentinel is a **free, open-source**, privacy-first AI agent that automates daily planning, communication triage, and decision support while maintaining strict human oversight. Built on OpenClaw principles of deny-by-default capabilities, verifiable execution, and human-in-the-loop governance, the system is a **proactive assistant** that adapts to different contexts: **personal use**, **family coordination**, and **enterprise/team operations**.

**Universal Value Proposition:**
- **Personal:** Reclaim 2-3 hours daily through intelligent scheduling, email triage, and proactive task management
- **Family:** Coordinate schedules, meal planning, weather alerts, and travel for the whole household
- **Enterprise:** Reduce operational overhead by 40% through automated workflows, compliance-aware approvals, and cross-functional coordination while maintaining audit trails required for SOC 2/GDPR

**Key Differentiator:** All capabilities available to everyone - no tiers, no restrictions, no paywalls. 

---

## 2. Vision & Strategic Goals

### 2.1 Vision Statement
**Democratize AI-powered productivity** by providing a free, open-source proactive agent that helps everyone - individuals, families, and organizations - focus on what matters most while automating routine tasks. Committed to user control, data privacy, and explainable AI decisions.

### 2.2 Primary Goals

| Goal | Personal Use | Family Use | Enterprise Use |
|------|--------------|------------|----------------|
| **Cognitive Load Reduction** | Automate inbox-to-calendar coordination | Coordinate family schedules and activities | Streamline cross-departmental scheduling and approval chains |
| **Proactive Assistance** | Morning briefings, weather alerts, calendar conflicts | Meal planning, weather for activities, shared tasks | Policy compliance monitoring, audit trails |
| **Decision Velocity** | Surface critical actions within 10 seconds | Family-friendly alerts and reminders | Manager escalation workflows with role-based authority |
| **Control Preservation** | Explicit opt-in for all external actions | Family member consent management | Granular RBAC with just-in-time privilege elevation |
| **Cross-Domain Utility** | Personal productivity + life management | Recipes, travel, education, healthcare | Industry-specific compliance (HIPAA, SOX, GDPR) |

---

## 3. Target Users & Personas

### 3.1 Personal Use Personas

**Persona A: The Knowledge Worker**
- *Profile:* Product manager, consultant, or creative professional
- *Pain Points:* Context switching between Slack, email, and calendar; missed follow-ups; overbooking
- *Success Metric:* 90% of routine scheduling handled without manual intervention

**Persona B: The Researcher/Graduate Student**
- *Profile:* Academic requiring deep work blocks and citation management
- *Pain Points:* Fragmented focus time, deadline tracking across multiple projects
- *Success Metric:* 4-hour uninterrupted focus blocks preserved 4x weekly

**Persona C: The Small Business Operator**
- *Profile:* Solo founder or freelancer managing client communications
- *Pain Points:* Invoice tracking, client meeting coordination, proposal deadlines
- *Success Metric:* Zero missed payment follow-ups; 50% reduction in scheduling back-and-forth

### 3.2 Family Use Personas

**Persona D: The Busy Parent**
- *Profile:* Working parent managing household logistics for 2-4 people
- *Pain Points:* Coordinating kids' activities, meal planning, grocery shopping, family calendar conflicts
- *Success Metric:* Family dinners 5x/week; zero missed school events; proactive weather alerts for outdoor activities

**Persona E: The Multi-Generational Household Coordinator**
- *Profile:* Adult managing schedules and care for children + elderly parents
- *Pain Points:* Medical appointments, medication tracking, coordinating caregivers, school events
- *Success Metric:* 100% medication adherence tracking; automated appointment reminders; caregiver schedule visibility

### 3.3 Enterprise/Team Use Personas

**Persona F: The Department Manager**
- *Profile:* Team lead in marketing, engineering, or operations
- *Pain Points:* Approval bottlenecks, resource allocation visibility, compliance documentation
- *Success Metric:* 80% of routine approvals (expenses, PTO, vendor payments) processed within 4 hours

**Persona G: The Healthcare Administrator**
- *Profile:* Clinic manager or medical practice coordinator
- *Pain Points:* Patient scheduling compliance, HIPAA-aware communication, staff coordination
- *Success Metric:* 100% audit trail coverage for all patient-data-adjacent automated actions

**Persona H: The Enterprise Security Officer**
- *Profile:* CISO or compliance manager evaluating AI tools
- *Pain Points:* Shadow AI adoption, ungoverned automation, secrets exposure
- *Success Metric:* Complete visibility into agent actions with immutable audit logs

---

## 4. Universal Capabilities (All Free & Open Source)

**All capabilities are available to everyone - no artificial restrictions:**

| Domain | Features |
|--------|----------|
| **Core Connectors** | Gmail, Google Calendar, Outlook, Slack, Todoist, Notion, Salesforce, SAP, Workday |
| **Email Triage** | Unlimited messages, intent classification, action extraction, custom rules, DLP scanning |
| **Approval Workflows** | Manual approvals, automation rules, multi-stage chains, delegation matrices |
| **System Monitoring** | Local device health, application usage tracking, optimization recommendations |
| **Document Access** | Local files, cloud storage (Drive/Dropbox), semantic search, summarization with citations |
| **Weather & Alerts** | Current conditions, forecasts, rain warnings, severe weather alerts, proactive notifications |
| **Research & Analysis** | Finance/stocks, politics, IT/tech, science, news - multi-domain research capabilities |
| **Food & Cooking** | Recipe search, cooking tips, ingredient sourcing, dietary restrictions support |
| **Travel & Transport** | Flights, trains, buses, real-time status, multi-modal comparison |
| **Team Coordination** | Shared calendars, project views, role-based workspaces, resource pooling |
| **Security** | OAuth, local encryption, SSO (Google/Microsoft), SAML 2.0, SCIM provisioning |
| **Audit & Compliance** | Immutable audit logs, SOC 2/HIPAA/GDPR compliance support, configurable retention |
| **Deployment** | Local desktop, cloud hybrid, on-premise, private cloud, VPC - user's choice |

**Community-Driven Development:** Features, connectors, and improvements contributed by the open-source community.

---

## 5. Core Capabilities (MVP - Phase 1)

### 5.1 Calendar Intelligence & Smart Scheduling

**Individual Use:**
- **Daily Briefing:** Concise morning summary (delivered via app, email, or Telegram) showing: today's schedule, focus block recommendations, and travel time buffers
- **Focus Protection:** Automatically reschedule non-essential meetings when deep-work blocks are threatened
- **Smart Buffering:** Insert 15-minute buffers between video calls to prevent "Zoom fatigue"

**Enterprise Use:**
- **Resource Optimization:** Coordinate across team calendars to find optimal meeting times considering role-based priorities (e.g., VP availability weighted higher than individual contributors)
- **Meeting Cost Calculator:** Surface meeting cost based on attendee salaries to encourage efficiency
- **Compliance Scheduling:** Healthcare-specific rules ensuring provider schedules meet regulatory rest requirements

**Technical Requirements:**
- Google Calendar API (OAuth 2.0), Microsoft Graph API, CalDAV support
- Conflict resolution algorithm with user-defined escalation rules
- Local caching for offline schedule viewing

### 5.2 Email Ingestion & Triage

**Individual Use:**
- **Intent Classification:** Categorize as Action Required, FYI, or Low Priority with >85% accuracy
- **Draft Generation:** Propose replies for routine requests (scheduling, document requests) with user review required before send
- **Newsletter Digest:** Auto-archive newsletters into weekly summary format

**Enterprise Use:**
- **Sensitive Data Detection:** Flag emails containing PII, financial data, or legal terms requiring special handling
- **Escalation Routing:** Auto-forward compliance-sensitive emails to legal/HR based on content analysis
- **Retention Policy Enforcement:** Auto-archive or delete per organizational data governance rules

**Technical Constraints & Safety:**
- **Rate Limiting:** Respect Gmail API quotas (250 quota units per user per second) 
- **Prompt Injection Defense:** Implement input sanitization and output filtering to prevent malicious email content from hijacking agent behavior 
- **No Automated Send Without Approval:** All outbound emails require explicit user confirmation (deny-by-default) 

### 5.3 Critical Action Detection & Approval Workflow

**Definition:** A "Critical Action" is any operation with material external side-effects affecting:
- Financial transactions or commitments >$100
- Legal obligations or contract modifications
- Data deletion or sharing outside organizational boundaries
- System configuration changes

**Individual Workflow:**
- **Approval Card UI:** Minimal, single-decision interface showing: proposed action, confidence score, data sources, and one-click options (Approve / Edit / Defer / Reject)
- **Context Preservation:** Show exactly which email or calendar event triggered the recommendation
- **Undo Capability:** 30-second "oops" window for all executed actions

**Enterprise Workflow:**
- **Policy Engine:** Configurable rules defining criticality thresholds by department (e.g., Marketing can auto-approve $500 expenses; Engineering requires VP approval for $1000+)
- **Delegation Chains:** Automatic escalation to manager if approval not processed within SLA
- **Audit Trail:** Immutable log of all approval decisions with timestamp, user identity, and justification

**Safety Architecture (OpenClaw-Compliant):**
- **Skill-Based Permissions:** Capabilities defined in markdown skill files with explicit permission scopes 
- **Sandboxed Execution:** Read-only mode available; write operations require explicit capability grants
- **Verifiable Execution:** Structured logs of every tool invocation with parameters and results 

### 5.4 Task Extraction & Unified Task List

**Capabilities:**
- Extract action items from emails, calendar invites, and manual notes
- Enrich with metadata: priority (Eisenhower matrix), estimated effort, deadline, source context
- Sync bidirectionally with external task managers (Todoist, Asana, Jira)

**Enterprise Enhancements:**
- **Project Mapping:** Auto-associate tasks with active projects based on email domains or keywords
- **Workload Balancing:** Manager dashboard showing team task load distribution
- **Sprint Integration:** Two-way sync with Agile tools, converting "reply to client" emails into sprint tickets

---

## 6. Extended Capabilities (Post-MVP)

### 6.1 Local System Integration (Personal Tier Lead)

**Device Monitoring & Health:**
- Monitor CPU, memory, disk, and battery; surface health recommendations in daily briefing
- **Privacy Control:** All monitoring local-only; no telemetry to cloud without explicit opt-in
- **Platform Support:** Windows initially (Phase 2), macOS (Phase 3), Linux (Phase 4)

**Document Intelligence:**
- Local semantic search across user documents (encrypted index)
- Summarization with source citation and provenance tracking
- **Safety:** Agent can only access files in explicitly granted directories; no system-wide file access

### 6.2 Advanced Messaging (Pro/Enterprise)

**Supported Platforms & Limitations:**

| Platform | Read/Notify | Send Automated | Enterprise Notes |
|----------|-------------|----------------|------------------|
| **Gmail/Outlook** | ✅ | ✅ (with approval) | Full API support |
| **Telegram** | ✅ | ✅ | Bot API allows full automation |
| **WhatsApp Business API** | ✅ | ⚠️ Templates only | Subject to 24-hour messaging window; requires Meta Business verification  |
| **Slack** | ✅ | ✅ | Workspace apps with granular scopes |
| **Microsoft Teams** | ✅ | ✅ | Graph API integration |
| **LINE** | ✅ | ⚠️ Limited | Official API restricted to approved partners |
| **Instagram/Facebook** | ⚠️ Read-only | ❌ Blocked | Meta API prohibits automated messaging for consumer accounts  |

**Risk Acknowledgment:** WhatsApp Business API requires official Meta partnership; consumer-grade WhatsApp automation violates Terms of Service and risks permanent account ban . OpenSentinel will only support official API pathways.

### 6.3 Enterprise Multi-Tenancy & Governance

**Workspace Architecture:**
- **Organization:** Top-level entity with centralized billing and policy management
- **Teams:** Sub-groups with shared project boards and resource calendars
- **Roles:** User, Manager, Admin, Auditor (read-only compliance access)

**Advanced Security:**
- **Just-In-Time Access:** Temporary privilege elevation for sensitive operations with automatic revocation 
- **Secrets Management:** Integration with enterprise vaults (HashiCorp Vault, Azure Key Vault, AWS Secrets Manager); no credentials stored in agent memory 
- **Behavioral Monitoring:** Anomaly detection for unusual agent activity patterns (e.g., 3x normal email deletion rate triggers security review)

---

## 7. Safety, Privacy & Governance Framework

### 7.1 Core Principles (OpenClaw Alignment)

| Principle | Implementation |
|-----------|----------------|
| **Deny-by-Default** | All capabilities require explicit opt-in; agent starts with zero permissions  |
| **Least Privilege** | Scoped tokens (read-only where possible); no SSH key access or system-wide file permissions  |
| **Human-in-the-Loop** | All external side-effects require user confirmation; confidence thresholds configurable per action type |
| **Verifiable Execution** | Immutable audit logs with structured execution records (what ran, what it accessed, what changed)  |
| **Supply Chain Security** | Skills cryptographically signed; community skills require explicit trust establishment |

### 7.2 Data Handling

**Personal Tier:**
- **Local-First Architecture:** Core processing on-device; cloud used only for cross-device sync (encrypted)
- **Data Minimization:** Retain only semantic summaries (not full email content) after 30 days
- **Easy Export/Purge:** One-click data download (JSON/CSV) and account deletion

**Enterprise Tier:**
- **Data Residency:** Configurable storage regions (US, EU, APAC) for GDPR compliance
- **Retention Policies:** Configurable per organizational requirements with legal hold capabilities
- **Encryption:** AES-256 at rest; TLS 1.3 in transit; optional customer-managed keys (CMK) for enterprise

### 7.3 Compliance Posture

| Regulation | Individual Compliance | Enterprise Compliance |
|------------|----------------------|----------------------|
| **GDPR** | Data portability, right to deletion, processing consent | DPO dashboard, data subject request automation, EU data residency |
| **CCPA** | Opt-out of data processing, disclosure of data categories | Automated compliance reporting, consumer request portal |
| **HIPAA** | N/A (not a covered entity) | Business Associate Agreement (BAA), PHI access logging, minimum necessary enforcement |
| **SOC 2 Type II** | N/A | Annual audit, controls documentation, penetration testing |

---

## 8. Technical Architecture

### 8.1 High-Level Components

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interface Layer                     │
│  (Desktop App, Web Dashboard, Mobile Companion, Browser Ext) │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                    Gateway Layer (Node.js)                   │
│  • Message routing & session management                      │
│  • Platform authentication (OAuth 2.0, device tokens)        │
│  • Security enforcement (allow-lists, rate limiting)         │
│  • Skill loading & permission scoping                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
┌──────────────┐ ┌──────────┐ ┌──────────────┐
│  Connectors  │ │  Policy  │ │   Suggestion │
│   Adapters   │ │  Engine  │ │    Engine    │
│              │ │          │ │              │
│ • Gmail API  │ │ • Risk   │ │ • Priority   │
│ • Graph API  │ │   scoring│ │   scoring    │
│ • CalDAV     │ │ • Approval│ │ • Timeboxing │
│ • IMAP       │ │   routing│ │ • Batching   │
└──────────────┘ └──────────┘ └──────────────┘
        │              │              │
        └──────────────┼──────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  Data Layer                                  │
│  • Local SQLite (Personal) / PostgreSQL (Enterprise)        │
│  • Encrypted vector store for semantic search               │
│  • Immutable audit log (append-only, signed)                │
└─────────────────────────────────────────────────────────────┘
```

### 8.2 Machine Learning Components

**NLP Extraction Pipeline:**
- Intent classification (email → action/FYI/spam)
- Named entity recognition (dates, amounts, people, projects)
- Sentiment analysis for urgency detection
- **Confidence Scoring:** All predictions include confidence; sub-threshold predictions trigger manual review

**Personalization Engine (Pro/Enterprise):**
- Learn user scheduling preferences (preferred meeting times, focus hours)
- Adapt triage rules based on user corrections (false positives/negatives)
- **Reset Capability:** Users can reset learned preferences without losing configuration

### 8.3 Security Architecture

**Authentication:**
- OAuth 2.0 for all third-party integrations (Google, Microsoft)
- PKCE (Proof Key for Code Exchange) for mobile/desktop apps
- Enterprise SSO via SAML 2.0 or OIDC

**Authorization:**
- Role-based access control (RBAC) with resource-level permissions
- Attribute-based access control (ABAC) for dynamic policies (e.g., "approve if amount < $500 and department = Marketing")

**Audit & Monitoring:**
- Structured execution logs: timestamp, actor (user/agent), action, parameters, result, confidence score
- Real-time alerting for anomalous patterns (e.g., bulk email deletion, unusual API call volumes)
- Integration with enterprise SIEM tools (Splunk, Datadog, Elastic)

---

## 9. Non-Functional Requirements

### 9.1 Performance

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Daily Briefing Generation | < 3 seconds | Time from app open to interactive briefing |
| Email Triage Latency | < 2 seconds per message | End-to-end from ingestion to classification |
| Approval Card Render | < 500ms | Time from notification to actionable UI |
| Calendar Conflict Resolution | < 1 second | Suggestion generation for scheduling conflicts |
| System Health Dashboard | < 5 seconds | Enterprise fleet overview load time |

### 9.2 Reliability

- **Availability:** 99.9% uptime for cloud-hosted components (Enterprise SLA)
- **Graceful Degradation:** Local functionality persists during cloud outages; sync resumes automatically
- **Data Integrity:** Checksums on all audit logs; automated backup verification
- **Disaster Recovery:** RPO (Recovery Point Objective) < 1 hour; RTO (Recovery Time Objective) < 4 hours for Enterprise tier

### 9.3 Scalability

- **Personal:** Single user, up to 5,000 emails/day, 10 connected calendars
- **Pro:** Up to 10 team members, 50,000 emails/day, 100 connected calendars
- **Enterprise:** Unlimited users, horizontal scaling of ingestion pipeline, multi-region deployment

---

## 10. Roadmap & Milestones

### Phase 0: Foundation (Weeks 1-4)
- [ ] Stakeholder validation of personas and edition tiers
- [ ] UX mockups: Approval Card, Daily Briefing, Inbox Triage
- [ ] Technical spike: OpenClaw Gateway integration, OAuth flows
- [ ] Security review: Threat modeling for prompt injection, secrets management

### Phase 1: Core MVP (Weeks 5-16)
**Deliverables:**
- Gmail + Google Calendar connectors (read-only initially)
- Email triage with >80% accuracy on validated test set
- Daily Briefing generation
- Manual approval workflows for all write operations
- Local audit logging
- Windows desktop app (local-first)

**Acceptance Criteria:**
- User can connect Gmail/Calendar via OAuth and view data within 30 seconds
- Daily briefing displays schedule + 3 prioritized actions when present
- Approval cards enable Approve/Defer decision in < 10 seconds
- Zero automated actions without explicit user confirmation

### Phase 2: Automation & Intelligence (Weeks 17-24)
- [ ] Smart scheduling with conflict resolution
- [ ] Task extraction and Todoist/Asana integration
- [ ] Basic automation rules (safe actions only: archive newsletters, schedule focus blocks)
- [ ] Document summarization (local files)
- [ ] Telegram connector
- [ ] macOS desktop app

### Phase 3: Enterprise & Team (Weeks 25-36)
- [ ] Multi-user workspaces and RBAC
- [ ] SSO (SAML 2.0) and SCIM provisioning
- [ ] Advanced connectors: Salesforce, Slack, Microsoft Teams
- [ ] Policy engine for automated approvals with guardrails
- [ ] Compliance reporting dashboard (GDPR, SOC 2)
- [ ] Customer-managed encryption keys
- [ ] iOS/Android companion apps

### Phase 4: Ecosystem & Scale (Weeks 37-52)
- [ ] WhatsApp Business API integration (official partner pathway)
- [ ] Industry-specific templates (healthcare, legal, financial services)
- [ ] AI marketplace for community skills (signed/verified)
- [ ] Advanced analytics and productivity insights
- [ ] On-premise deployment option

---

## 11. Acceptance Criteria (Detailed)

### 11.1 Functional Criteria

| ID | Requirement | Test Method |
|----|-------------|-------------|
| AC-001 | Daily briefing displays calendar events for next 24h + at least 3 prioritized action items | Manual UI test with seeded data |
| AC-002 | Email triage achieves >80% precision/recall on Enron dataset (public benchmark) | Automated classification test |
| AC-003 | Approval workflow blocks all external side-effects without explicit user confirmation | Security penetration testing |
| AC-004 | OAuth connection flow completes successfully for Gmail, Outlook, and Google Calendar | Integration test with sandbox accounts |
| AC-005 | Local document search returns relevant results in < 2 seconds for 10,000 document index | Performance benchmark |
| AC-006 | Audit log captures all agent actions with immutable timestamp and actor identity | Log integrity verification |

### 11.2 Security Criteria

| ID | Requirement | Verification |
|----|-------------|--------------|
| SEC-001 | No long-lived credentials stored in agent memory or configuration files  | Code audit, memory dump analysis |
| SEC-002 | All skills operate with explicitly granted permissions (deny-by-default)  | Integration test with restricted skill set |
| SEC-003 | Prompt injection attempts are detected and neutralized without executing malicious instructions  | Red team exercise with known attack patterns |
| SEC-004 | Secrets rotation completes without service interruption | Automated rotation drill |
| SEC-005 | User data purge completes within 24 hours of request with certificate of deletion | GDPR compliance audit |

---

## 12. Risk Assessment & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Prompt Injection Attacks** | Medium | High | Layered defenses: input sanitization, output filtering, tool approval workflows, scoped permissions  |
| **Secrets Exposure** | Medium | Critical | Secretless patterns, just-in-time access, hardware security modules (HSM) for enterprise  |
| **API Rate Limiting** | High | Medium | Exponential backoff, request queuing, graceful degradation to manual mode |
| **WhatsApp/Meta API Restrictions** | High | High | Official Business API partnership only; clear messaging on consumer account limitations  |
| **Data Residency Violations** | Low | Critical | Configurable regions, EU data centers, GDPR-compliant processing agreements |
| **User Trust Erosion** | Medium | High | Transparent audit logs, local-first options, easy data export, no dark patterns |
| **Enterprise Sales Cycle** | High | Medium | Freemium individual tier drives bottom-up adoption; clear ROI calculator for enterprise |

---

## 13. Open Questions

1. **Local LLM Support:** Should we support on-device LLM inference (e.g., Llama 3, Mistral) for air-gapped enterprise deployments?
2. **Mobile Strategy:** Is a companion app sufficient, or do we need full mobile parity for enterprise field workers?
3. **Partnership Strategy:** Should we pursue formal partnerships with Google Workspace/Microsoft 365 or remain connector-agnostic?
4. **Healthcare Expansion:** Do we invest in HIPAA compliance for Phase 2, or defer to Phase 3 pending market validation?

---

## 14. Glossary

| Term | Definition |
|------|------------|
| **OpenClaw** | Open-source AI agent framework emphasizing safety, local execution, and skill-based capabilities  |
| **Critical Action** | Any operation with material external side-effects affecting finances, legal standing, or data governance |
| **Skill** | Modular capability definition (Markdown-based) declaring what an agent can do and what permissions it requires  |
| **Human-in-the-Loop (HITL)** | Design pattern requiring human approval before executing high-risk automated actions |
| **Prompt Injection** | Attack vector where malicious input manipulates AI agent behavior  |
| **SCIM** | System for Cross-domain Identity Management (automated user provisioning) |
| **CMK** | Customer-Managed Keys (enterprise encryption control) |

---

## 15. References

1. OpenClaw Architecture & Security Principles 
2. CrowdStrike: AI Agent Runtime Protection 
3. Akeyless: AI Agent Identity Security 
4. Auth0: Securing AI Agents Best Practices 
5. WhatsApp Business API Policy Documentation 
6. Enterprise GRC Frameworks for AI 

---

**Document Owner:** Product Management  
**Reviewers:** Engineering Lead, Security Officer, Legal Counsel  
**Next Review Date:** 2026-03-21

 