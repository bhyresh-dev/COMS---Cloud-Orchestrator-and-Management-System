export default function Security() {
  return (
    <div className="min-h-full bg-[#080b14] px-8 py-10">
      <div className="max-w-3xl">
        <div className="mb-10">
          <h1 className="text-2xl font-semibold text-white tracking-tight">Security</h1>
          <p className="mt-1.5 text-sm text-white/40">
            Technical documentation on access controls, AI scopes, and audit mechanisms.
          </p>
        </div>

        <div className="space-y-6">
          <Section title="Authentication">
            <p>
              Every protected API endpoint extracts the <Code>Authorization: Bearer</Code> header
              and verifies it using the Firebase Admin SDK. Revoked and expired tokens receive a{' '}
              <Code>401</Code>. There is no anonymous access path and no fallback to a weaker
              mechanism.
            </p>
          </Section>

          <Section title="Role-Based Access Control">
            <p>
              Two roles exist: <Code>user</Code> and <Code>admin</Code>. Role values are stored
              in Firestore keyed by Firebase UID and read on every request. Token claims are not
              trusted. New accounts default to <Code>user</Code>. Promotion to{' '}
              <Code>admin</Code> requires manual Firestore editing — no UI or API endpoint exists.
            </p>
            <div className="mt-4 bg-[#0d0f17] border border-white/[0.07] rounded-xl overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/[0.06]">
                    {['Endpoint', 'user', 'admin'].map(h => (
                      <th key={h} className="px-4 py-3 text-left text-[11px] font-semibold text-white/30 uppercase tracking-widest">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.04]">
                  {[
                    ['POST /api/nlp/process',          'S3 only', 'S3 only'],
                    ['GET /api/buckets',               'Own',     'All'],
                    ['DELETE /api/buckets/:name',      'Own',     'Any'],
                    ['GET /api/audit',                 'Own',     'All'],
                    ['GET /api/approvals',             'Own',     'All'],
                    ['POST /api/approvals/:id/approve','403',     'Allowed'],
                    ['GET /api/admin/*',               '403',     'Allowed'],
                  ].map(([ep, u, a]) => (
                    <tr key={ep} className="hover:bg-white/[0.02]">
                      <td className="px-4 py-2.5 font-mono text-xs text-white/55">{ep}</td>
                      <td className={`px-4 py-2.5 text-xs ${u === '403' ? 'text-red-400' : 'text-white/45'}`}>{u}</td>
                      <td className="px-4 py-2.5 text-xs text-white/45">{a}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Section>

          <Section title="AI Automation Scope">
            <p>
              The <Code>POST /api/nlp/process</Code> endpoint runs the NLP → policy → risk →
              execute pipeline. After parsing, the server checks the resolved intent against
              an allowlist. Any intent outside the allowlist is rejected with <Code>403</Code>{' '}
              and an <Code>ai_scope_violation</Code> entry is written to the audit log.
            </p>
            <p>
              Permitted intents: <Code>create_s3_bucket</Code>, <Code>create_iam_role</Code>,{' '}
              <Code>launch_ec2_instance</Code>, <Code>create_lambda_function</Code>,{' '}
              <Code>create_sns_topic</Code>, <Code>create_log_group</Code>.
            </p>
            <p>
              This prevents the AI layer from listing or deleting resources, reading bucket
              contents, or acting outside the explicit create allowlist.
            </p>
          </Section>

          <Section title="Policy Enforcement">
            <p>
              Before any resource creation, the policy engine queries Firestore for the user's
              current live resource count and compares it to limits in{' '}
              <Code>config/policies.json</Code>. S3 buckets are capped at 10 per user. Limits
              are checked on every request with no caching.
            </p>
          </Section>

          <Section title="Audit Logging">
            <p>
              Every create, delete, approve, reject, and policy denial writes to the{' '}
              <Code>audit_logs</Code> Firestore collection: action name, status, user UID,
              email, role, and UTC timestamp. The collection is append-only. No endpoint exists
              to delete or modify log entries.
            </p>
          </Section>

          <Section title="Credentials">
            <p>
              No AWS credentials or Firebase keys are hardcoded. All secrets load from
              environment variables at startup. Missing required credentials cause an immediate{' '}
              <Code>sys.exit</Code>. In <Code>production</Code> mode, CORS is locked to
              <Code>CORS_ORIGIN</Code>; if unset, startup is aborted.
            </p>
          </Section>
        </div>
      </div>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div className="bg-[#0d0f17] border border-white/[0.07] rounded-2xl p-6">
      <h2 className="text-sm font-semibold text-white mb-3">{title}</h2>
      <div className="space-y-2.5 text-sm text-white/50 leading-relaxed">
        {children}
      </div>
    </div>
  );
}

function Code({ children }) {
  return (
    <code className="font-mono text-xs bg-white/[0.07] text-white/70 px-1.5 py-0.5 rounded">
      {children}
    </code>
  );
}
