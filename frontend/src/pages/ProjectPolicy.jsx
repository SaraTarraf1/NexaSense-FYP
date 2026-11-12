import { Link } from 'react-router-dom';
import './ProjectPolicy.css';

const policies = {
  terms: {
    title: 'Terms of Use',
    introduction: 'These terms describe the use of NexaSense, an academic final-year project for equipment inspection and monitoring.',
    sections: [
      ['About the project', 'NexaSense is a prototype under development. Features may be incomplete or change during testing. Equipment monitoring, sensor integration and automated inspection features are being developed in stages; demonstration readings may be simulated.'],
      ['Your account', 'Provide accurate registration information, keep your password private and use only accounts and equipment you are authorized to access. Tell the project team if you suspect someone has accessed your account without permission.'],
      ['Acceptable use', 'Use NexaSense for authorized learning, testing and inspection activities. Do not attempt to access another user’s data, interfere with the system, upload harmful content or submit information you do not have permission to share.'],
      ['Inspection results and safety', 'Readings, alerts and any automated analysis support maintenance decisions. They do not replace professional inspections, manufacturer guidance or emergency safety procedures. Do not rely on this prototype for safety-critical decisions. Verify unexpected results with a qualified person.'],
      ['Availability and changes', 'During development, the service may be interrupted and test data may be reset. Keep separate copies of any records you need. Review these terms when the project introduces new features.'],
      ['Questions', 'Ask the NexaSense project team through the person who invited you to the project or your existing course or project communication channel.'],
    ],
  },
  privacy: {
    title: 'Privacy Policy',
    introduction: 'This notice describes the current NexaSense academic prototype. Share only information needed to test and use the project.',
    sections: [
      ['Registration information', 'Registration sends your full name, email address and password to the NexaSense API. The application stores your name, email address, a password hash, account role, active status and account creation time in its database. The registration handler hashes your password before storing it.'],
      ['How information is used', 'Account information is used to create and administer your account and identify duplicate email registrations. The agreement checkbox is sent with your registration request for validation. It is not currently stored as a separate consent record.'],
      ['Equipment and inspection information', 'Equipment records, sensor readings and inspection history are planned project features. Their collection and use should be described here before those features are introduced. Do not submit private facility details or real sensor data through demonstration fields unless the project team has explained how they will be handled.'],
      ['Access and storage', 'Account records are held in the database configured for the running project. People who administer that application or database may have access to account information. This notice does not promise a particular hosting location or external sharing arrangement; ask the project team about the deployment you are using.'],
      ['Keeping, correcting or deleting information', 'The prototype does not currently provide self-service account deletion or a fixed automatic deletion schedule. Contact the project team through your existing project or course communication channel to ask about reviewing, correcting or deleting your information and how long test records will be kept.'],
      ['Browser storage and external services', 'The current registration page does not save your password or form entries in browser storage. The registration code does not add analytics or advertising trackers. Browser tools, hosting services and future features may have their own data handling, which should be reviewed before wider use.'],
      ['Updates and questions', 'This notice should be updated as data collection, hosting and project features change. Ask the person who invited you to NexaSense to connect you with the project team if you have privacy questions.'],
    ],
  },
};

export default function ProjectPolicy({ type }) {
  const policy = policies[type];
  return (
    <main className="policy-page">
      <article className="policy-card" aria-labelledby="policy-title">
        <Link className="policy-back" to="/register">← Back to registration</Link>
        <p className="policy-brand">NexaSense · Inspection &amp; Monitoring</p>
        <h1 id="policy-title">{policy.title}</h1>
        <p className="policy-date">Updated November 12, 2026 · Academic prototype</p>
        <p>{policy.introduction}</p>
        {policy.sections.map(([heading, content]) => (
          <section key={heading}><h2>{heading}</h2><p>{content}</p></section>
        ))}
        <nav aria-label="Project policies">
          <Link to={type === 'terms' ? '/privacy' : '/terms'}>
            Read the {type === 'terms' ? 'Privacy Policy' : 'Terms of Use'}
          </Link>
        </nav>
      </article>
    </main>
  );
}
