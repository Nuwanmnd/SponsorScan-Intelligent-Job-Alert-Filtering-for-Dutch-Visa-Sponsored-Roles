import React, { useEffect, useState } from 'react';
import axios from 'axios';
import {
  ExternalLink,
  CheckCircle,
  XCircle,
  Clock,
  Trash2,
  LayoutDashboard,
  ListChecks,
  Sparkles,
  ShieldCheck,
  FileText,
} from 'lucide-react';

const API_URL = 'http://127.0.0.1:8000';

const emptyAnalysis = null;
const emptyTailoring = null;

const SimpleList = ({ items, icon }) => (
  <ul>
    {items?.map((item) => (
      <li key={item}>{icon ? <>{icon} </> : null}{item}</li>
    ))}
  </ul>
);

const SectionNotesCard = ({ title, notes }) => (
  <div className="column-card">
    <h3>{title}</h3>

    <h4>Keep</h4>
    <SimpleList items={notes.keep} />

    <h4 className="subheading">Remove / Reduce</h4>
    <SimpleList items={notes.remove} />

    <h4 className="subheading">Rewrite / Reorder</h4>
    <SimpleList items={notes.rewrite} />
  </div>
);

const CVSectionBlock = ({ title, items, text }) => {
  const hasItems = Array.isArray(items) && items.length > 0;
  const hasText = typeof text === 'string' && text.trim();

  if (!hasItems && !hasText) {
    return null;
  }

  return (
    <div className="cv-draft-block">
      <h4>{title}</h4>
      {hasText ? <p className="summary-box">{text}</p> : null}
      {hasItems ? <SimpleList items={items} /> : null}
    </div>
  );
};

const App = () => {
  const [jobs, setJobs] = useState([]);
  const [tab, setTab] = useState('latest');
  const [loading, setLoading] = useState(true);
  const [jobDescription, setJobDescription] = useState('');
  const [analysis, setAnalysis] = useState(emptyAnalysis);
  const [tailoring, setTailoring] = useState(emptyTailoring);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [tailoringLoading, setTailoringLoading] = useState(false);
  const [aiError, setAiError] = useState('');

  useEffect(() => {
    fetchJobs();
  }, []);

  const fetchJobs = async () => {
    try {
      setLoading(true);
      const res = await axios.get(`${API_URL}/jobs`);
      setJobs(res.data);
    } catch (err) {
      console.error('Error fetching jobs:', err);
    } finally {
      setLoading(false);
    }
  };

  const refreshJobs = async () => {
    try {
      setLoading(true);
      await axios.post(`${API_URL}/jobs/refresh`);
      await fetchJobs();
    } catch (err) {
      console.error('Error refreshing jobs:', err);
      alert('Failed to refresh jobs. Check console.');
    } finally {
      setLoading(false);
    }
  };

  const updateStatus = async (id, status) => {
    try {
      await axios.put(`${API_URL}/jobs/${id}`, { status });
      setJobs(jobs.map((job) => (job.id === id ? { ...job, status } : job)));
    } catch (err) {
      console.error('Error updating status:', err);
    }
  };

  const applyJob = (job) => {
    if (job.link) {
      window.open(job.link, '_blank');
      updateStatus(job.id, 'applied');
      return;
    }
    alert('No link available for this job.');
  };

  const extractApiError = (error, fallbackMessage) =>
    error?.response?.data?.detail || fallbackMessage;

  const analyzeDescription = async () => {
    if (!jobDescription.trim()) {
      setAiError('Paste a job description first.');
      return;
    }

    try {
      setAiError('');
      setAnalysisLoading(true);
      setTailoring(emptyTailoring);
      const res = await axios.post(`${API_URL}/ai/analyze`, {
        job_description: jobDescription,
      });
      setAnalysis(res.data);
    } catch (err) {
      console.error('Error analyzing job description:', err);
      setAiError(extractApiError(err, 'Failed to analyze the job description.'));
    } finally {
      setAnalysisLoading(false);
    }
  };

  const tailorApplication = async () => {
    if (!jobDescription.trim()) {
      setAiError('Paste a job description first.');
      return;
    }

    try {
      setAiError('');
      setTailoringLoading(true);
      const res = await axios.post(`${API_URL}/ai/tailor`, {
        job_description: jobDescription,
      });
      setTailoring(res.data);
    } catch (err) {
      console.error('Error tailoring application:', err);
      setAiError(extractApiError(err, 'Failed to tailor your application materials.'));
    } finally {
      setTailoringLoading(false);
    }
  };

  const latestJobs = jobs.filter((job) => job.status === 'pending');
  const appliedJobs = jobs.filter((job) => ['applied', 'rejected', 'approved'].includes(job.status));

  return (
    <div className="container">
      <header>
        <div className="topbar">
          <div>
            <h1>Job Alert Dashboard</h1>
            <p className="hero-copy">
              Track sponsor-matched roles, then pressure-test a job description before applying to check eligibility and probability of success.
            </p>
          </div>
          <button
            className="btn btn-primary"
            onClick={refreshJobs}
            disabled={loading}
          >
            <Clock size={18} /> {loading ? 'Refreshing...' : 'Refresh Inbox'}
          </button>
        </div>

        <div className="tabs">
          <button
            className={`tab btn ${tab === 'latest' ? 'active' : ''}`}
            onClick={() => setTab('latest')}
          >
            <LayoutDashboard size={18} /> New Opportunities
          </button>
          <button
            className={`tab btn ${tab === 'applied' ? 'active' : ''}`}
            onClick={() => setTab('applied')}
          >
            <ListChecks size={18} /> Applied Tracker
          </button>
          <button
            className={`tab btn ${tab === 'ai' ? 'active' : ''}`}
            onClick={() => setTab('ai')}
          >
            <Sparkles size={18} /> AI Match Review
          </button>
        </div>
      </header>

      {tab !== 'ai' ? (
        <main className="card">
          {loading ? (
            <div className="empty-state">Loading...</div>
          ) : (
            <table>
              <thead>
                {tab === 'latest' ? (
                  <tr>
                    <th>Date</th>
                    <th>Job Title & Company</th>
                    <th className="align-right">Actions</th>
                  </tr>
                ) : (
                  <tr>
                    <th>Job Title</th>
                    <th>Company</th>
                    <th>Status</th>
                  </tr>
                )}
              </thead>
              <tbody>
                {tab === 'latest' ? (
                  latestJobs.length > 0 ? latestJobs.map((job) => (
                    <tr key={job.id}>
                      <td>
                        <div className="inline-meta">
                          <Clock size={14} className="text-muted" />
                          {new Date(job.date_found).toLocaleDateString()}
                        </div>
                      </td>
                      <td>
                        <div className="job-title">{job.title}</div>
                        <div className="company-name">{job.company}</div>
                      </td>
                      <td className="align-right">
                        <div className="action-row">
                          <button
                            className="btn btn-danger"
                            onClick={() => updateStatus(job.id, 'ignored')}
                          >
                            <Trash2 size={16} /> Ignore
                          </button>
                          <button
                            className="btn btn-primary"
                            onClick={() => applyJob(job)}
                          >
                            Apply <ExternalLink size={16} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  )) : (
                    <tr>
                      <td colSpan="3" className="empty-state">
                        No new matches found. Check back later!
                      </td>
                    </tr>
                  )
                ) : (
                  appliedJobs.length > 0 ? appliedJobs.map((job) => (
                    <tr key={job.id}>
                      <td><div className="job-title">{job.title}</div></td>
                      <td><div className="company-name">{job.company}</div></td>
                      <td>
                        <select
                          value={job.status}
                          onChange={(event) => updateStatus(job.id, event.target.value)}
                          className={`status-badge status-${job.status}`}
                        >
                          <option value="applied">Applied / Pending</option>
                          <option value="approved">Approved</option>
                          <option value="rejected">Rejected</option>
                        </select>
                      </td>
                    </tr>
                  )) : (
                    <tr>
                      <td colSpan="3" className="empty-state">
                        You haven&apos;t tracked any applications yet.
                      </td>
                    </tr>
                  )
                )}
              </tbody>
            </table>
          )}
        </main>
      ) : (
        <main className="ai-layout">
          <section className="card ai-panel">
            <div className="section-header">
              <div>
                <h2>Manual Job Review</h2>
                <p className="section-copy">
                  Paste a LinkedIn job description and compare it against your background before you apply.
                </p>
              </div>
            </div>

            <label className="field-label ai-field-label" htmlFor="job-description">
              Job discription
            </label>
            <textarea
              id="job-description"
              className="job-textarea"
              value={jobDescription}
              onChange={(event) => {
                setJobDescription(event.target.value);
                setAnalysis(emptyAnalysis);
                setTailoring(emptyTailoring);
                setAiError('');
              }}
              placeholder="Paste the full LinkedIn job description here..."
            />

            <div className="action-row left">
              <button
                className="btn btn-primary"
                onClick={analyzeDescription}
                disabled={analysisLoading}
              >
                <ShieldCheck size={18} />
                {analysisLoading ? 'Analyzing...' : 'Analyze'}
              </button>
              <button
                className="btn btn-secondary"
                onClick={tailorApplication}
                disabled={tailoringLoading || !analysis}
              >
                <FileText size={18} />
                {tailoringLoading ? 'Tailoring...' : 'Tailor CV + Cover Letter'}
              </button>
            </div>

            {aiError ? <div className="error-box">{aiError}</div> : null}
          </section>

          {analysis ? (
            <section className="card ai-panel">
              <div className="section-header">
                <div>
                  <h2>Analysis Result</h2>
                  <p className="section-copy">
                    A quick view of fit, seriousness, and whether this looks worth your time.
                  </p>
                </div>
                <div className="score-pill">
                  <span>Fit Score</span>
                  <strong>{analysis.fit_score}/100</strong>
                </div>
              </div>

              <div className="analysis-grid">
                <div className="insight-card">
                  <h3>Fit Summary</h3>
                  <p>{analysis.fit_summary}</p>
                </div>
                <div className="insight-card">
                  <h3>Legitimacy / Quality</h3>
                  <p>{analysis.legitimacy_assessment}</p>
                </div>
                <div className="insight-card">
                  <h3>How Serious Is It?</h3>
                  <p>{analysis.seriousness_assessment}</p>
                </div>
                <div className="insight-card">
                  <h3>Recommendation</h3>
                  <p>{analysis.recommendation}</p>
                </div>
              </div>

              <div className="list-grid">
                <div className="bullet-card">
                  <h3>Why It Matches</h3>
                  <ul>
                    {analysis.match_reasons.map((item) => (
                      <li key={item}><CheckCircle size={16} /> {item}</li>
                    ))}
                  </ul>
                </div>
                <div className="bullet-card">
                  <h3>Concerns</h3>
                  <ul>
                    {analysis.concerns.map((item) => (
                      <li key={item}><XCircle size={16} /> {item}</li>
                    ))}
                  </ul>
                </div>
              </div>

              <div className="next-step-box">
                <h3>Suggested Next Step</h3>
                <p>{analysis.next_step}</p>
              </div>
            </section>
          ) : null}

          {tailoring ? (
            <section className="card ai-panel">
              <div className="section-header">
                <div>
                  <h2>Tailored Application Draft</h2>
                  <p className="section-copy">
                    Role-specific CV decisions, a structured one-page draft, and a ready-to-copy cover letter.
                  </p>
                </div>
              </div>

              <div className="two-column">
                <div className="column-card">
                  <h3>Recommended CV Title</h3>
                  <p className="summary-box">{tailoring.recommended_cv_title}</p>

                  <h3 className="subheading">Recommended Profile Summary</h3>
                  <p className="summary-box">{tailoring.recommended_profile_summary}</p>

                  <h3 className="subheading">Key Points To Highlight</h3>
                  <SimpleList items={tailoring.key_points_to_highlight} />

                  <h3 className="subheading">Optional Extra Details</h3>
                  <SimpleList items={tailoring.optional_extra_details} />

                  <h3 className="subheading">What Not To Claim</h3>
                  <SimpleList items={tailoring.what_not_to_claim} />
                </div>

                <div className="column-card">
                  <h3>Final One-Page CV Draft</h3>

                  <CVSectionBlock title="Title" text={tailoring.final_one_page_cv_draft.title} />
                  <CVSectionBlock title="Profile Summary" text={tailoring.final_one_page_cv_draft.profile_summary} />
                  <CVSectionBlock title="Skills" items={tailoring.final_one_page_cv_draft.skills} />
                  <CVSectionBlock title="Experience" items={tailoring.final_one_page_cv_draft.experience} />
                  <CVSectionBlock title="Projects" items={tailoring.final_one_page_cv_draft.projects} />
                  <CVSectionBlock title="Education" items={tailoring.final_one_page_cv_draft.education} />
                  <CVSectionBlock title="Additional Sections" items={tailoring.final_one_page_cv_draft.additional_sections} />
                </div>
              </div>

              <div className="section-notes-grid">
                <SectionNotesCard title="General Structure" notes={tailoring.section_notes.general_structure} />
                <SectionNotesCard title="Skills" notes={tailoring.section_notes.skills} />
                <SectionNotesCard title="Projects" notes={tailoring.section_notes.projects} />
                <SectionNotesCard title="Experience" notes={tailoring.section_notes.experience} />
                <SectionNotesCard title="Education" notes={tailoring.section_notes.education} />
              </div>

              <section className="card nested-card">
                <div className="ai-panel">
                  <h2>Tailored Cover Letter</h2>
                  <pre className="cover-letter-output">{tailoring.cover_letter}</pre>
                </div>
              </section>
            </section>
          ) : null}
        </main>
      )}
    </div>
  );
};

export default App;
