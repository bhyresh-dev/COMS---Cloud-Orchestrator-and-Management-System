"""
COMS — Cloud Orchestrator and Management System
Powered by: Groq (Llama 3.3 70B) + AWS Free Tier + SQLite
"""
import streamlit as st
import time
import json
import csv
import io
from datetime import datetime

# ── PAGE CONFIG (must be first) ──────────────────────────
st.set_page_config(
    page_title="COMS",
    page_icon="☁️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ──────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Plus+Jakarta+Sans:wght@400;600;700&display=swap');

.stApp { font-family: 'Plus Jakarta Sans', sans-serif; }

.main-header {
    font-size: 1.8rem; font-weight: 700; color: #00E5A0;
    display: flex; align-items: center; gap: 10px;
}
.badge {
    display: inline-block; padding: 3px 10px; border-radius: 20px;
    font-size: 0.72rem; font-weight: 600; color: white;
}
.badge-green  { background: #00C48C; }
.badge-blue   { background: #0070F3; }
.badge-orange { background: #F5A623; }
.badge-red    { background: #E53E3E; }
.badge-grey   { background: #4A5568; }

.pipeline-step {
    background: #0d1117; border-left: 3px solid #00E5A0;
    padding: 8px 16px; margin: 4px 0; border-radius: 0 8px 8px 0;
    font-family: 'JetBrains Mono', monospace; font-size: 0.82rem; color: #e6edf3;
}
.resource-card {
    background: #0d1117; border: 1px solid #21262d; border-radius: 10px;
    padding: 14px; margin: 6px 0;
}
.security-badge {
    background: #1a1f2e; border: 1px solid #2d3548; border-radius: 8px;
    padding: 10px; font-size: 0.78rem; color: #8b949e;
}
.warning-box {
    background: #2d2000; border-left: 3px solid #F5A623;
    padding: 8px 14px; border-radius: 0 8px 8px 0;
    font-size: 0.82rem; color: #F5A623; margin: 4px 0;
}
</style>
""", unsafe_allow_html=True)

# ── AUTH ─────────────────────────────────────────────────
try:
    from utils.auth import get_authenticator, get_user_role
    authenticator, auth_config = get_authenticator()
    authenticator.login()
    auth_status = st.session_state.get("authentication_status")
    username = st.session_state.get("username", "")
    AUTH_ENABLED = True
except Exception:
    # If streamlit-authenticator not installed, fall back to role selector
    auth_status = True
    username = "demo_user"
    AUTH_ENABLED = False

if AUTH_ENABLED and auth_status is False:
    st.error("Incorrect username or password.")
    st.stop()

if AUTH_ENABLED and auth_status is None:
    st.info("👋 Welcome to **COMS** — please log in.")
    st.caption("Default credentials — admin/Admin@123 · devlead/DevLead@123 · dev/Dev@1234")
    st.stop()

# ── IMPORTS (after auth guard) ────────────────────────────
from agents.orchestrator import MasterOrchestrator, do_approve, do_reject
from utils.database import (
    get_audit_log, get_recent_logs, get_audit_stats,
    get_pending_approvals, get_all_approvals, get_resources,
    get_monthly_spend,
)
from utils.aws_client import AWS_MODE

# ── SESSION STATE ─────────────────────────────────────────
if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = MasterOrchestrator()
if "messages" not in st.session_state:
    st.session_state.messages = []

# Determine role
if AUTH_ENABLED and username:
    try:
        user_role = get_user_role(username)
    except Exception:
        user_role = "developer"
else:
    user_role = "developer"

if "user_role" not in st.session_state:
    st.session_state.user_role = user_role

st.session_state.orchestrator.set_user_role(st.session_state.user_role)
st.session_state.orchestrator.set_username(username)

# ── SIDEBAR ───────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="main-header">☁️ COMS</div>', unsafe_allow_html=True)

    aws_color = "badge-blue" if "Real" in AWS_MODE else "badge-grey"
    st.markdown(
        f'<span class="badge badge-green">● Online</span> '
        f'<span class="badge {aws_color}">{AWS_MODE}</span>',
        unsafe_allow_html=True,
    )
    st.caption("AI-Powered Cloud Orchestration — Free Tier Edition")
    st.markdown("---")

    # Role selector (overrides auth role for demo purposes)
    if not AUTH_ENABLED:
        st.session_state.user_role = st.selectbox(
            "🔑 Role", ["developer", "dev-lead", "admin"],
            help="In production this comes from SSO automatically."
        )
        st.session_state.orchestrator.set_user_role(st.session_state.user_role)
    else:
        role_colors = {"admin": "badge-red", "dev-lead": "badge-orange", "developer": "badge-blue"}
        badge_cls = role_colors.get(st.session_state.user_role, "badge-grey")
        st.markdown(
            f'👤 **{username}** &nbsp; <span class="badge {badge_cls}">{st.session_state.user_role}</span>',
            unsafe_allow_html=True,
        )

    st.markdown("---")

    page = st.radio("Navigate", [
        "💬 Chat",
        "🛡️ Admin Approvals",
        "📦 Resource Inventory",
        "📊 Dashboard",
        "📜 Audit Log",
    ])

    st.markdown("---")
    st.markdown("**🎯 Quick Demo**")
    demos = {
        "⚡ S3 Bucket": "Create a private S3 bucket for the backend team in ap-south-1",
        "λ Lambda Function": "Create a Python Lambda function called data-processor",
        "📣 SNS Topic": "Create an SNS topic called order-notifications",
        "🔍 List Resources": "List all my S3 buckets",
        "🤔 Vague Request": "I need some compute resources",
        "🔒 IAM (High Risk)": "Create an IAM admin role with full access",
    }
    for label, prompt_text in demos.items():
        if st.button(label, key=f"demo_{label}", use_container_width=True):
            st.session_state.pending_demo = prompt_text

    st.markdown("---")
    if st.button("🔄 New Conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.orchestrator.reset()
        st.rerun()

    if AUTH_ENABLED:
        st.markdown("---")
        try:
            authenticator.logout("🚪 Logout", "sidebar")
        except Exception:
            pass

    st.markdown("---")
    st.markdown('<div class="security-badge">🔐 Zero credential exposure — users never see AWS keys. RBAC enforced per role.</div>', unsafe_allow_html=True)


def _render_pipeline(stages: list):
    if not stages:
        return
    st.markdown("---\n**Pipeline:**")
    for stage in stages:
        icon = "✅" if stage.get("status") in ["success", "approved"] else "❌" if stage.get("status") == "error" else "⚠️"
        st.markdown(
            f'<div class="pipeline-step">{icon} {stage["stage"]} — {stage["time_seconds"]}s</div>',
            unsafe_allow_html=True,
        )


# ════════════════════════════════════════════════════════════
# PAGE: CHAT
# ════════════════════════════════════════════════════════════
if page == "💬 Chat":
    st.markdown("## ☁️ COMS — Chat Interface")
    col_info, col_mode = st.columns([3, 1])
    with col_info:
        st.caption(f"Role: **{st.session_state.user_role}** · LLM: Llama 3.3 70B (Groq) · AWS: {AWS_MODE}")
    with col_mode:
        if "Real" not in AWS_MODE:
            st.warning("⚠️ LocalStack mode — not real AWS")
        else:
            st.success("✅ Real AWS Free Tier")

    # Display history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"], unsafe_allow_html=True)

    # Input
    prompt = None
    if "pending_demo" in st.session_state:
        prompt = st.session_state.pop("pending_demo")
    else:
        prompt = st.chat_input("Describe your cloud resource request in plain English...")

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("⚡ Processing through pipeline..."):
                result = st.session_state.orchestrator.process_message(prompt)

            response = ""

            if result["status"] == "clarification_needed":
                response = f"🤔 **Need more info:**\n\n{result['message']}"
                st.markdown(response)

            elif result["status"] == "denied":
                response = "🚫 **Request Denied by Policy Engine**\n\n"
                for v in result.get("violations", []):
                    response += f"❌ {v}\n\n"
                warnings = result.get("warnings", [])
                if warnings:
                    response += "\n⚠️ **Warnings:**\n"
                    for w in warnings:
                        response += f"  - {w}\n"
                st.markdown(response)

            elif result["status"] == "pending_approval":
                risk = result.get("risk_result", {})
                aid = result.get("approval_id", "?")
                response = (
                    f"⏳ **Awaiting Admin Approval** (Request #{aid})\n\n"
                    f"**Risk Level:** {risk.get('tier', 'High Risk')}\n\n"
                    f"**Reason:** {risk.get('reason', '')}\n\n"
                    "👉 Go to **🛡️ Admin Approvals** in the sidebar."
                )
                st.markdown(response)
                _render_pipeline(result.get("pipeline_stages", []))

            elif result["status"] == "executed":
                resource = result.get("resource", {})
                st.markdown(f"✅ **{result['message']}**")
                if resource:
                    st.markdown("**Provisioned Resource:**")
                    num_cols = min(len(resource), 4)
                    if num_cols > 0:
                        cols = st.columns(num_cols)
                        for i, (key, val) in enumerate(resource.items()):
                            with cols[i % num_cols]:
                                st.metric(label=key.replace("_", " ").title(), value=str(val))
                _render_pipeline(result.get("pipeline_stages", []))
                response = f"✅ Done in {result['total_time_seconds']}s"

            elif result["status"] == "error":
                response = f"⚠️ **Error:** {result.get('message', 'Unknown error')}"
                st.markdown(response)

            st.session_state.messages.append({"role": "assistant", "content": response or result.get("message", "")})


# ════════════════════════════════════════════════════════════
# PAGE: ADMIN APPROVALS
# ════════════════════════════════════════════════════════════
elif page == "🛡️ Admin Approvals":
    st.markdown("## 🛡️ Admin Approval Queue")

    if st.session_state.user_role not in ("admin", "dev-lead"):
        st.error("🚫 Access denied. Admin or Dev-Lead role required.")
        st.stop()

    tab_pending, tab_history = st.tabs(["⏳ Pending", "📋 History"])

    with tab_pending:
        pending = get_pending_approvals()
        if not pending:
            st.success("✅ No pending approvals. Queue is clear!")
        else:
            st.info(f"**{len(pending)} request(s) awaiting approval**")
            for entry in pending:
                parsed = entry["parsed_request"]
                risk = entry["risk_result"]
                with st.expander(
                    f"🔶 #{entry['id']} — {parsed.get('intent','?')} | {entry['user_role']} | {entry['timestamp']}",
                    expanded=True,
                ):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown(f"**Intent:** `{parsed.get('intent')}`")
                        st.markdown(f"**Service:** `{parsed.get('service')}`")
                        st.markdown(f"**Risk:** {risk.get('tier')}")
                        st.markdown(f"**Requested by:** `{entry['user_role']}`")
                    with c2:
                        st.markdown("**Parameters:**")
                        st.json(parsed.get("parameters", {}))

                    reject_reason = st.text_input(
                        "Rejection reason (optional)", key=f"reason_{entry['id']}"
                    )
                    btn_a, btn_r = st.columns(2)
                    with btn_a:
                        if st.button(f"✅ Approve #{entry['id']}", key=f"approve_{entry['id']}", use_container_width=True):
                            res = do_approve(entry["id"], username)
                            if res["status"] == "executed":
                                st.success(f"✅ Approved & Executed: {res['message']}")
                            else:
                                st.error(f"Execution failed: {res.get('message')}")
                            time.sleep(1)
                            st.rerun()
                    with btn_r:
                        if st.button(f"❌ Reject #{entry['id']}", key=f"reject_{entry['id']}", use_container_width=True):
                            do_reject(entry["id"], reject_reason or "Rejected by admin", username)
                            st.warning("Request rejected.")
                            time.sleep(1)
                            st.rerun()

    with tab_history:
        all_approvals = get_all_approvals(50)
        resolved = [a for a in all_approvals if a["status"] != "pending"]
        if not resolved:
            st.info("No resolved approvals yet.")
        else:
            for a in resolved:
                color = "✅" if a["status"] == "approved" else "❌"
                st.markdown(
                    f'<div class="pipeline-step">{color} #{a["id"]} — '
                    f'{a["parsed_request"].get("intent","?")} | '
                    f'**{a["status"].upper()}** | {a.get("resolved_at","?")[:19]} '
                    f'by {a.get("resolved_by","?")}</div>',
                    unsafe_allow_html=True,
                )


# ════════════════════════════════════════════════════════════
# PAGE: RESOURCE INVENTORY
# ════════════════════════════════════════════════════════════
elif page == "📦 Resource Inventory":
    st.markdown("## 📦 Resource Inventory")
    st.caption("All resources provisioned through COMS (active only)")

    resources = get_resources("active")

    if not resources:
        st.info("No active resources yet. Use Chat to provision resources.")
    else:
        # Group by type
        by_type: dict = {}
        for r in resources:
            by_type.setdefault(r["resource_type"], []).append(r)

        service_icons = {
            "S3 Bucket": "🪣",
            "EC2 Instance": "🖥️",
            "IAM Role": "🔑",
            "Lambda Function": "λ",
            "SNS Topic": "📣",
            "CloudWatch Log Group": "📋",
        }

        for rtype, items in by_type.items():
            icon = service_icons.get(rtype, "☁️")
            st.markdown(f"### {icon} {rtype} ({len(items)})")
            for item in items:
                with st.expander(f"`{item['resource_name']}` — {item['timestamp'][:19]}", expanded=False):
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Region", item.get("region") or "global")
                    c2.metric("Created by", item.get("created_by_role") or "?")
                    c3.metric("Status", item["status"])
                    if item["details"]:
                        st.json(item["details"])
            st.markdown("---")

    # Export
    if resources:
        csv_buf = io.StringIO()
        writer = csv.DictWriter(csv_buf, fieldnames=["id", "timestamp", "resource_type", "resource_name", "region", "status", "created_by_role"])
        writer.writeheader()
        for r in resources:
            writer.writerow({k: r.get(k, "") for k in writer.fieldnames})
        st.download_button(
            "⬇️ Export Inventory (CSV)",
            data=csv_buf.getvalue(),
            file_name=f"coms_inventory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
        )


# ════════════════════════════════════════════════════════════
# PAGE: DASHBOARD
# ════════════════════════════════════════════════════════════
elif page == "📊 Dashboard":
    st.markdown("## 📊 Monitoring Dashboard")

    stats = get_audit_stats()
    resources = get_resources("active")
    monthly_spend = get_monthly_spend()
    pending_count = len(get_pending_approvals())

    # Metrics row
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Requests", stats["total"])
    c2.metric("Successful", stats["success"])
    c3.metric("Errors", stats["errors"])
    c4.metric("Pending Approval", pending_count)
    c5.metric("Active Resources", len(resources))

    st.markdown("---")

    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("### ⏱ Traditional ITSM vs COMS")
        st.error("**Traditional ITSM**\n\nTicket → Approval → Provisioning: **4–48 hours** ❌")
        st.success("**COMS**\n\nNLP → Validate → Execute: **< 5 seconds** ✅")

    with col_right:
        st.markdown("### 💰 AWS Free Tier Status")
        st.info(
            "**This app runs entirely on AWS Free Tier:**\n\n"
            "- S3: 5 GB / month (free 12 months)\n"
            "- EC2: 750 hrs t2.micro / month (free 12 months)\n"
            "- Lambda: 1M requests / month (forever free)\n"
            "- SNS: 1M publishes / month (forever free)\n"
            "- IAM: Always free\n"
            "- CloudWatch Logs: 5 GB ingestion free\n\n"
            f"**Estimated monthly cost: $0.00** ✅"
        )

    st.markdown("---")
    st.markdown("### ☁️ AWS Mode")
    if "Real" in AWS_MODE:
        st.success(f"**{AWS_MODE}** — Resources are created in real AWS. Free tier applies.")
        st.markdown("""
**How to stay in free tier:**
- Only create t2.micro / t3.micro EC2 instances (already enforced by policy)
- S3 bucket storage limited to 5 GB (enforced by policy)
- Lambda + SNS always free
- Terminate EC2 instances when not in use
""")
    else:
        st.warning(f"**{AWS_MODE}** — Commands go to LocalStack (localhost:4566), not real AWS.")
        st.markdown("""
**To switch to Real AWS Free Tier and create actual S3 buckets by prompting:**
1. Sign up at [aws.amazon.com/free](https://aws.amazon.com/free)
2. Go to IAM → Create user → Attach `AmazonS3FullAccess`, `AmazonEC2FullAccess`, `IAMFullAccess`, `AWSLambda_FullAccess`, `AmazonSNSFullAccess`
3. Generate Access Keys
4. Edit `.env`:
   ```
   AWS_ACCESS_KEY_ID=your_real_key
   AWS_SECRET_ACCESS_KEY=your_real_secret
   AWS_DEFAULT_REGION=ap-south-1
   # Remove or comment out: AWS_ENDPOINT_URL=http://localhost:4566
   ```
5. Restart the app → all prompts now create real AWS resources!
""")

    st.markdown("---")
    st.markdown("### 📈 Recent Activity")
    recent = get_recent_logs(10)
    if recent:
        for entry in recent:
            icon = "✅" if entry["status"] == "success" else "❌" if entry["status"] == "error" else "⚠️"
            ts = entry["timestamp"][:19] if entry.get("timestamp") else "?"
            st.markdown(
                f'<div class="pipeline-step">{icon} <b>{entry["action"]}</b> | {ts} | {entry["status"].upper()}</div>',
                unsafe_allow_html=True,
            )
    else:
        st.info("No activity yet.")


# ════════════════════════════════════════════════════════════
# PAGE: AUDIT LOG
# ════════════════════════════════════════════════════════════
elif page == "📜 Audit Log":
    st.markdown("## 📜 Audit Trail")

    logs = get_audit_log(200)

    if not logs:
        st.info("No actions recorded yet.")
    else:
        # Filters
        fc1, fc2 = st.columns(2)
        with fc1:
            status_filter = st.multiselect(
                "Filter by status", ["success", "error", "denied", "pending", "approved", "rejected"],
                default=[]
            )
        with fc2:
            action_filter = st.text_input("Filter by action keyword", "")

        filtered = logs
        if status_filter:
            filtered = [l for l in filtered if l["status"] in status_filter]
        if action_filter:
            filtered = [l for l in filtered if action_filter.lower() in l["action"].lower()]

        st.caption(f"Showing {len(filtered)} of {len(logs)} entries")

        for entry in filtered:
            icon = "✅" if entry["status"] in ("success", "approved") else "❌" if entry["status"] in ("error", "denied") else "⚠️"
            ts = entry.get("timestamp", "?")[:19]
            role = f" | {entry['user_role']}" if entry.get("user_role") else ""
            dur = f" | {entry['duration_s']}s" if entry.get("duration_s") else ""
            st.markdown(
                f'<div class="pipeline-step">{icon} <b>{entry["action"]}</b>'
                f' | {ts}{role}{dur}'
                f' | <b>{entry["status"].upper()}</b></div>',
                unsafe_allow_html=True,
            )

        # Export
        st.markdown("---")
        csv_buf = io.StringIO()
        writer = csv.DictWriter(csv_buf, fieldnames=["id", "timestamp", "action", "status", "user_role", "duration_s", "details"])
        writer.writeheader()
        for l in filtered:
            writer.writerow({
                "id": l.get("id", ""),
                "timestamp": l.get("timestamp", ""),
                "action": l.get("action", ""),
                "status": l.get("status", ""),
                "user_role": l.get("user_role", ""),
                "duration_s": l.get("duration_s", ""),
                "details": l.get("details", ""),
            })
        st.download_button(
            "⬇️ Export Audit Log (CSV)",
            data=csv_buf.getvalue(),
            file_name=f"coms_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
        )
