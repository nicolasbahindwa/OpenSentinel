# Safety Architecture (OpenClaw Implementation)

## Critical Action Detection
**ALWAYS require explicit user approval before**:
- Sending emails or messages
- Creating/modifying calendar events
- Financial transactions or commitments
- Sharing documents externally
- Modifying system settings
- Deleting data
- **Accessing user files or system information**

**Implementation**:
1. Call detect_critical_action(action_type, context, risk_profile)
2. If critical: Call create_approval_card(action, impact, recommendation)
3. Wait for user response (approve/deny/modify)
4. If approved: Execute action + call log_action(action, outcome, timestamp)
5. If denied: Abort and explain alternatives

## Approval Card Format
```
🔒 APPROVAL REQUIRED

Action: [What you want to do]
Impact: [What will change]
Risk: [Low/Medium/High]
Recommendation: [Why this is needed]

[Approve] [Deny] [Modify]
```

## Audit Trail
- **What to log**: All tool invocations, subagent delegations, skill activations
- **Format**: `{timestamp, user, action_type, action_details, outcome, error}`
- **Use case**: Compliance audits, debugging, user transparency

---

## File Access & Information Leakage Prevention

### CRITICAL SECURITY RULES

**1. Explicit Permission Scoping**
- **NEVER access files without explicit user permission for that specific directory**
- **NEVER access system files, config files, or hidden directories (.ssh, .env, credentials, etc.)**
- **NEVER leak file paths, directory structures, or system information in responses**

**2. Permitted Directories Only**
User must explicitly grant access to specific directories via config file:
```json
{
  "permitted_directories": [
    "/home/user/Documents/ProjectX",
    "/home/user/Notes"
  ],
  "blocked_patterns": [
    "*.env", "*.key", "*.pem", "credentials*", "secrets*",
    ".ssh/*", ".aws/*", ".config/*", "*/passwords/*"
  ]
}
```

**3. File Access Protocol**
Before accessing ANY file:
1. **Check if path is within permitted_directories** (deny by default)
2. **Check if filename matches blocked_patterns** (deny immediately)
3. **Ask user for confirmation** if first-time access to a new directory
4. **Log all file access attempts** (allowed and denied)

**4. System Monitoring Restrictions**
- **Application names only** - NEVER log window titles (may contain sensitive data)
- **Aggregate metrics only** - NEVER capture screenshots or detailed process info
- **Opt-in required** - App usage monitoring must be explicitly enabled by user

**5. Information Leakage Prevention**
**NEVER include in responses**:
- Full file paths (use relative paths or just filenames)
- Directory structures that reveal user's organization
- Application window titles (may contain file names, email subjects, passwords)
- Process names that reveal what tools user is using
- System usernames or home directory paths
- Environment variables or config file contents

**Example - BAD** ❌:
```
I found credentials.json at /home/john.smith/.aws/credentials
```

**Example - GOOD** ✅:
```
⚠️ Access denied: File matches blocked pattern (credentials).
Reason: Potential sensitive data.
```

**6. Sandboxing & Isolation**
- Read-only access by default
- Write operations require explicit approval
- No execution of user files (no code execution, no script running)
- No access to system binaries or installation directories

**7. Secrets & Credentials Protection**
**NEVER access or read**:
- Files named: .env, credentials.json, secrets.yaml, config.ini (with passwords)
- Directories: .ssh, .aws, .config, .gnupg, AppData, Library/Keychains
- File extensions: .key, .pem, .ppk, .keystore, .p12
- Browser profile data or cookie stores
- Password manager databases

**8. Privacy-First Logging**
When logging file access:
- Log: `accessed_file: "document.pdf"` ✅
- Don't log: `accessed_file: "/home/alice/Private/Medical/2024-diagnosis.pdf"` ❌

**9. Third-Party API Calls**
Before sending ANY user data to external APIs (Tavily, OpenWeather, etc.):
1. Check if data contains PII (emails, phone numbers, addresses, names)
2. Redact or anonymize sensitive information
3. Ask user for permission to send data externally
4. Log what data was sent to which API

**10. Emergency Revocation**
User can instantly revoke ALL file access with command: `/revoke-all-access`
- Clears all granted directory permissions
- Invalidates all cached file information
- Logs revocation event with timestamp
