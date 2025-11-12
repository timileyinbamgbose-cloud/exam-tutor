# Bug Report Template
**ExamsTutor AI - Alpha Testing**
**Phase 4: Pilot Testing**

---

## Bug Report #[NUMBER]

**Date:** YYYY-MM-DD
**Reporter:** [Your Name/Username]
**Role:** [Student/Teacher/Admin]
**Environment:** [Alpha/Beta/Production]

---

### 1. Bug Summary
**Title:** [Brief, descriptive title]

**Severity:** [Select One]
- ⛔ **Critical** - System crash, data loss, security vulnerability
- 🔴 **High** - Major feature broken, blocking user workflow
- 🟡 **Medium** - Feature partially broken, workaround available
- 🟢 **Low** - Minor issue, cosmetic, typo

**Priority:** [Select One]
- 🚨 **P0** - Fix immediately (Critical bugs)
- 🔥 **P1** - Fix in current sprint (High severity)
- ⚡ **P2** - Fix in next sprint (Medium severity)
- 📝 **P3** - Fix when possible (Low severity)

---

### 2. Bug Description

**What happened?**
[Clear description of the bug]

**What should have happened?**
[Expected behavior]

**How is this impacting you?**
[Impact on your workflow/experience]

---

### 3. Steps to Reproduce

1. [First step]
2. [Second step]
3. [Third step]
...

**Reproducibility:** [Select One]
- ✅ Always (100% of the time)
- 🔄 Often (>50% of the time)
- ⚠️ Sometimes (<50% of the time)
- ❓ Once (Cannot reproduce)

---

### 4. Environment Details

**Device Information:**
- Device: [Desktop/Laptop/Tablet/Phone]
- OS: [Windows 11/macOS 14/Android 13/iOS 17]
- Browser: [Chrome 119/Safari 17/Firefox 120] (if web app)
- Screen Size: [1920x1080/2560x1440/Mobile]
- Internet Connection: [WiFi/Mobile Data/Offline]

**Application Information:**
- Version: [0.4.0]
- Build: [Alpha/Beta]
- User Role: [Student/Teacher/Admin]
- Account: [test username]

---

### 5. Screenshots/Videos

**Attach files here:**
- [ ] Screenshot of the issue
- [ ] Screen recording (if applicable)
- [ ] Console logs (if technical)
- [ ] Network logs (if API issue)

**File names:**
- screenshot_bug_[NUMBER]_[DATE].png
- recording_bug_[NUMBER]_[DATE].mp4

---

### 6. Logs & Technical Details

**Error Messages:**
```
[Paste any error messages here]
```

**Console Logs:**
```
[Paste browser console logs if available]
```

**API Response:**
```json
{
  "error": "error message",
  "status_code": 500
}
```

**Request Details:**
- Endpoint: `/api/v1/tutor/ask`
- Method: `POST`
- Payload: `{...}`

---

### 7. Workaround

**Is there a workaround?**
- [x] Yes - [Describe workaround]
- [ ] No

---

### 8. Additional Context

**Related Issues:**
- Bug #[NUMBER] - [Similar issue]

**Notes:**
[Any additional information that might help]

---

### 9. Suggested Fix (Optional)

**If you have ideas on how to fix this:**
[Your suggestion]

---

## For QA Team Use Only

**Status:** [Select One]
- 🆕 New
- ✅ Confirmed
- 🔧 In Progress
- 🧪 Testing
- ✔️ Fixed
- ❌ Won't Fix
- 🔄 Duplicate of #[NUMBER]

**Assigned To:** [Developer Name]

**Sprint:** [Sprint Number]

**Fix Version:** [0.4.1]

**QA Notes:**
[Notes from QA team]

---

## Examples

### Example 1: Critical Bug

**Bug Summary:** System crashes when submitting math question with LaTeX

**Severity:** ⛔ Critical
**Priority:** 🚨 P0

**Bug Description:**
When I type a math question using LaTeX notation (e.g., `$$\frac{1}{2}$$`), the system crashes and I'm logged out.

**Steps to Reproduce:**
1. Log in as student
2. Go to "Ask Question" page
3. Type: "Solve $$\frac{x}{2} + 3 = 5$$"
4. Click "Submit"
5. System crashes, shows error page

**Reproducibility:** ✅ Always

**Environment:**
- Device: Laptop
- OS: Windows 11
- Browser: Chrome 119
- Account: student_ss2_average

**Screenshot:** [Attached]

---

### Example 2: Medium Bug

**Bug Summary:** Learning plan timeline shows incorrect dates

**Severity:** 🟡 Medium
**Priority:** ⚡ P2

**Bug Description:**
My learning plan shows "Start: Nov 1, End: Nov 30" but the timeline visualization displays "Nov 1 - Dec 1". The end date is off by one day.

**Steps to Reproduce:**
1. Log in as student
2. Go to "My Learning Plan"
3. Check the dates in the header vs. the timeline graph

**Reproducibility:** ✅ Always

**Workaround:** Yes - I can still use the plan, just ignore the visual timeline

**Environment:**
- Device: Desktop
- OS: macOS 14
- Browser: Safari 17

---

### Example 3: Low Priority Bug

**Bug Summary:** Typo in diagnostic report: "weaknes" instead of "weakness"

**Severity:** 🟢 Low
**Priority:** 📝 P3

**Bug Description:**
In the diagnostic report, there's a typo: "Your main weaknes is..." should be "weakness"

**Steps to Reproduce:**
1. Complete diagnostic test
2. View report
3. See typo in first paragraph

**Screenshot:** [Attached]

---

## Submission

**Submit to:**
- GitHub Issues: https://github.com/examstutor/ai-api/issues
- Email: bugs@examstutor.ng
- Slack: #alpha-bugs channel

**Before submitting:**
- [ ] I've checked for duplicate reports
- [ ] I've filled in all required fields
- [ ] I've attached relevant screenshots/logs
- [ ] I've tested with the latest version

---

**Thank you for helping us improve ExamsTutor AI!** 🙏
