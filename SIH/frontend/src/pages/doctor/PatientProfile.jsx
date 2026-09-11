import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Icon from '../../components/common/Icons';
import RadarFingerprint from '../../components/charts/RadarFingerprint';
import TrendLineChart from '../../components/charts/TrendLineChart';
import { fetchPatientDetail, savePatientNote, updatePatientDifficulty, updatePatientDetails } from '../../data/api';

const DETAIL_FIELDS = [
  { key: 'stage', label: 'Diagnosis / Clinical Stage' },
  { key: 'riskStatus', label: 'Risk Status' },
  { key: 'age', label: 'Age' },
  { key: 'gender', label: 'Gender' },
  { key: 'primaryCaregiver', label: 'Primary Caregiver' },
  { key: 'phone', label: 'Caregiver Phone' },
];

export default function PatientProfile() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [patient, setPatient] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [domains, setDomains] = useState(null);
  const [editingNotes, setEditingNotes] = useState(false);
  const [noteText, setNoteText] = useState('');
  const [editingDetails, setEditingDetails] = useState(false);
  const [detailsDraft, setDetailsDraft] = useState({});
  const [difficultyError, setDifficultyError] = useState('');
  const [detailsError, setDetailsError] = useState('');

  useEffect(() => {
    async function loadData() {
      const data = await fetchPatientDetail(id || 'patient-1');
      if (data && data.patient) {
        setPatient(data.patient);
        setNoteText(typeof data.patient.notes === 'string' ? data.patient.notes : data.patient.notes?.[0]?.text || '');
        setDetailsDraft(data.patient);
        setSessions(data.sessions || []);
        setDomains(data.cognitive_domains || null);
      }
    }
    loadData();
  }, [id]);

  if (!patient) {
    return (
      <div className="container text-center" style={{ padding: '4rem 1.5rem' }}>
        <h2>Patient profile not found.</h2>
        <button onClick={() => navigate('/doctor')} className="btn btn-primary" style={{ marginTop: '1.5rem' }}>
          Back to Roster
        </button>
      </div>
    );
  }

  const handleSaveNotes = async () => {
    await savePatientNote(patient.id, noteText);
    const updated = { ...patient, notes: noteText };
    setPatient(updated);
    setEditingNotes(false);
  };

  const handleDifficultyOverride = async (newDiff) => {
    setDifficultyError('');
    const previous = patient.difficulty;
    // Optimistic update, but roll back if the backend rejects it (e.g. a
    // non-clinical account, or the request fails) so the UI never shows a
    // pace that wasn't actually saved.
    setPatient({ ...patient, difficulty: newDiff });
    const result = await updatePatientDifficulty(patient.id, newDiff);
    if (result?.error) {
      setPatient({ ...patient, difficulty: previous });
      setDifficultyError(result.error);
      return;
    }
    const updated = { ...patient, difficulty: newDiff };
    setPatient(updated);
  };

  const handleSaveDetails = async () => {
    setDetailsError('');
    const changes = {};
    for (const { key } of DETAIL_FIELDS) {
      if (detailsDraft[key] !== patient[key]) {
        changes[key] = key === 'age' ? Number(detailsDraft[key]) || null : detailsDraft[key];
      }
    }
    if (Object.keys(changes).length === 0) {
      setEditingDetails(false);
      return;
    }
    const result = await updatePatientDetails(patient.id, changes);
    if (result?.error) {
      setDetailsError(result.error);
      return;
    }
    const updated = { ...patient, ...changes };
    setPatient(updated);
    setEditingDetails(false);
  };

  // Aggregated Analytics
  const totalSessions = sessions.length;
  const avgScore = totalSessions > 0
    ? Math.round(sessions.reduce((acc, s) => acc + s.score, 0) / totalSessions)
    : 0;
  const avgAccuracy = totalSessions > 0
    ? Math.round(sessions.reduce((acc, s) => acc + s.accuracy, 0) / totalSessions)
    : 0;
  const totalMistakes = totalSessions > 0
    ? sessions.reduce((acc, s) => acc + s.mistakes, 0)
    : 0;
  const avgResponseTime = totalSessions > 0
    ? Math.round((sessions.reduce((acc, s) => acc + s.responseTimeSec, 0) / totalSessions) * 10) / 10
    : 0;

  return (
    <div className="container-wide" style={{ padding: '2.5rem 1.5rem' }}>
      {/* Top Bar Navigation */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <button
          onClick={() => navigate('/doctor')}
          className="btn btn-secondary btn-small"
        >
          <Icon name="arrow-right" size={16} style={{ transform: 'rotate(180deg)' }} />
          <span>Back to Patient Roster</span>
        </button>

        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.35rem' }}>
          <div style={{ display: 'flex', gap: '0.6rem', alignItems: 'center' }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--color-text-muted)' }}>
              Starting Difficulty:
            </span>
            {['Easy', 'Medium', 'Hard'].map((lvl) => (
              <button
                key={lvl}
                onClick={() => handleDifficultyOverride(lvl)}
                className={`btn btn-small ${patient.difficulty === lvl ? 'btn-primary' : 'btn-secondary'}`}
              >
                {lvl}
              </button>
            ))}
          </div>
          {difficultyError && (
            <span style={{ fontSize: '0.8rem', color: 'var(--color-danger)' }}>{difficultyError}</span>
          )}
        </div>
      </div>

      {/* Patient Header Card */}
      <div className="smriti-card" style={{ marginBottom: '1.75rem', borderLeft: '5px solid var(--color-primary)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1.5rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
              <h1 style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 800, color: 'var(--color-primary)' }}>
                {patient.name}
              </h1>
              <span className={`badge badge-${patient.riskStatus === 'Stable' || patient.riskStatus === 'Improving' ? 'easy' : 'hard'}`}>
                {patient.riskStatus}
              </span>
              <span className="badge badge-neutral">Pace: {patient.difficulty}</span>
            </div>

            <div style={{ display: 'flex', gap: '1.75rem', flexWrap: 'wrap', marginTop: '0.75rem', fontSize: '0.95rem', color: 'var(--color-text-body)' }}>
              <span><strong>Age:</strong> {patient.age} yrs ({patient.gender})</span>
              <span><strong>Clinical Stage:</strong> {patient.stage}</span>
              <span><strong>Primary Caregiver:</strong> {patient.primaryCaregiver} ({patient.phone})</span>
              <span><strong>Physician:</strong> {patient.doctorAssigned || 'Dr. Ananya Sharma'}</span>
            </div>
          </div>

          <div style={{ textAlign: 'right' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Registered Since</span>
            <div style={{ fontWeight: 700, marginTop: '0.2rem' }}>{patient.registeredDate}</div>
          </div>
        </div>
      </div>

      {/* Editable Clinical Details */}
      <div className="smriti-card" style={{ marginBottom: '1.75rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.85rem' }}>
          <h2 style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--color-text-title)' }}>
            Patient Details
          </h2>
          {!editingDetails ? (
            <button onClick={() => { setEditingDetails(true); setDetailsDraft(patient); }} className="btn btn-secondary btn-small">
              Edit Details
            </button>
          ) : (
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button onClick={handleSaveDetails} className="btn btn-primary btn-small">Save</button>
              <button onClick={() => { setEditingDetails(false); setDetailsDraft(patient); setDetailsError(''); }} className="btn btn-secondary btn-small">Cancel</button>
            </div>
          )}
        </div>

        {detailsError && (
          <p style={{ fontSize: '0.85rem', color: 'var(--color-danger)', marginBottom: '0.75rem' }}>{detailsError}</p>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' }}>
          {DETAIL_FIELDS.map(({ key, label }) => (
            <div key={key}>
              <div style={{ fontSize: '0.78rem', textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--color-text-muted)', fontWeight: 700, marginBottom: '0.25rem' }}>
                {label}
              </div>
              {editingDetails ? (
                <input
                  className="form-control"
                  value={detailsDraft[key] ?? ''}
                  onChange={(e) => setDetailsDraft({ ...detailsDraft, [key]: e.target.value })}
                />
              ) : (
                <div style={{ fontWeight: 600, color: 'var(--color-text-body)' }}>
                  {patient[key] || <em style={{ color: 'var(--color-text-muted)', fontWeight: 400 }}>Not set</em>}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Clinical KPI Cards */}
      <div className="result-metric-tiles" style={{ marginBottom: '2rem' }}>
        <div className="metric-tile-box">
          <div className="metric-tile-number">{avgScore}%</div>
          <div className="metric-tile-label">Mean Session Score</div>
        </div>
        <div className="metric-tile-box">
          <div className="metric-tile-number" style={{ color: 'var(--color-success)' }}>{avgAccuracy}%</div>
          <div className="metric-tile-label">Average Accuracy</div>
        </div>
        <div className="metric-tile-box">
          <div className="metric-tile-number" style={{ color: totalMistakes > 5 ? 'var(--color-danger)' : 'var(--color-primary)' }}>
            {totalMistakes}
          </div>
          <div className="metric-tile-label">Recorded Mistakes</div>
        </div>
        <div className="metric-tile-box">
          <div className="metric-tile-number" style={{ color: 'var(--color-accent)' }}>
            {avgResponseTime}s
          </div>
          <div className="metric-tile-label">Average Reaction Time</div>
        </div>
      </div>

      {/* Visual Charts Grid: Longitudinal Line Chart + Cognitive Radar */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(460px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
        {/* Chart 1: Longitudinal Trends */}
        <div className="smriti-card">
          <h2 style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--color-primary)', marginBottom: '0.35rem' }}>
            Longitudinal Progress Over Time
          </h2>
          <p style={{ fontSize: '0.88rem', color: 'var(--color-text-muted)', marginBottom: '1.25rem' }}>
            Tracks score progression and reaction time across historical exercise sessions.
          </p>
          <TrendLineChart sessions={sessions} height={320} />
        </div>

        {/* Chart 2: Cognitive Fingerprint Radar */}
        <div className="smriti-card">
          <h2 style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--color-primary)', marginBottom: '0.35rem' }}>
            Cognitive Domain Radar Evaluation
          </h2>
          <p style={{ fontSize: '0.88rem', color: 'var(--color-text-muted)', marginBottom: '1.25rem' }}>
            Multidimensional evaluation across memory, orientation, semantics, and navigation.
          </p>
          <RadarFingerprint domainData={domains} height={320} />
        </div>
      </div>

      {/* Clinical Notes Card */}
      <div className="smriti-card" style={{ marginBottom: '2rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.85rem' }}>
          <h2 style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--color-text-title)' }}>
            Clinical Observation Notes & Pacing Strategy
          </h2>
          {!editingNotes ? (
            <button
              onClick={() => setEditingNotes(true)}
              className="btn btn-secondary btn-small"
            >
              Edit Notes
            </button>
          ) : (
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button onClick={handleSaveNotes} className="btn btn-primary btn-small">
                Save
              </button>
              <button onClick={() => setEditingNotes(false)} className="btn btn-secondary btn-small">
                Cancel
              </button>
            </div>
          )}
        </div>

        {editingNotes ? (
          <textarea
            className="form-control"
            rows="3"
            value={noteText}
            onChange={(e) => setNoteText(e.target.value)}
            placeholder="Record therapeutic observations, caregiver feedback, or clinical notes..."
          />
        ) : (
          <p style={{ color: 'var(--color-text-body)', fontSize: '0.95rem', fontStyle: noteText ? 'normal' : 'italic' }}>
            {noteText || 'No clinical notes recorded yet. Click Edit Notes to enter observations.'}
          </p>
        )}
      </div>

      {/* Full Activity History Table */}
      <div className="smriti-card">
        <h2 style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--color-text-title)', marginBottom: '1rem' }}>
          Activity Engagement History Log
        </h2>

        <div className="data-table-container">
          <table className="data-table" aria-label="Session History">
            <thead>
              <tr>
                <th>Date</th>
                <th>Activity Name</th>
                <th>Score</th>
                <th>Accuracy</th>
                <th>Mistakes</th>
                <th>Reaction Time</th>
                <th>Pacing</th>
                <th>Adaptive Decision</th>
                <th>Clinical Note</th>
              </tr>
            </thead>
            <tbody>
              {sessions.length === 0 ? (
                <tr>
                  <td colSpan="9" style={{ textAlign: 'center', padding: '3rem', color: 'var(--color-text-muted)' }}>
                    No sessions logged yet for this patient.
                  </td>
                </tr>
              ) : (
                sessions.slice().reverse().map((sess) => (
                  <tr key={sess.sessionId}>
                    <td>{sess.date}</td>
                    <td><strong>{sess.activityName}</strong></td>
                    <td style={{ fontWeight: 800, color: sess.score >= 80 ? 'var(--color-success)' : 'var(--color-warning)' }}>
                      {sess.score}%
                    </td>
                    <td>{sess.accuracy}%</td>
                    <td>{sess.mistakes}</td>
                    <td>{sess.responseTimeSec}s</td>
                    <td><span className="badge badge-neutral">{sess.difficulty}</span></td>
                    <td>
                      <span className="badge badge-easy">
                        {sess.newDifficulty || sess.difficulty}
                      </span>
                    </td>
                    <td style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)', maxWidth: '240px' }}>
                      {sess.feedbackNote || 'Session completed successfully.'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
