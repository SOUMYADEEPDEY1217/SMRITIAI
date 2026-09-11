import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Icon from '../../components/common/Icons';
import { analyzeMemoryPhoto, saveVerifiedMemory, listMemories } from '../../data/api';

export default function MemoriesPage() {
  const navigate = useNavigate();
  const [memories, setMemories] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    loadMemories();
  }, []);

  async function loadMemories() {
    setLoading(true);
    const data = await listMemories();
    setMemories(Array.isArray(data) ? data : []);
    setLoading(false);
  }

  return (
    <div className="container" style={{ padding: '2.5rem 1.5rem' }}>
      {/* Header */}
      <section className="patient-header-banner" style={{ marginBottom: '2rem' }}>
        <div>
          <span className="badge-overline">Memory Vault</span>
          <h1 className="patient-greeting-title">My Memories</h1>
          <p style={{ fontSize: '1.05rem', color: 'var(--color-text-body)', marginTop: '0.4rem', maxWidth: '600px' }}>
            Browse your cherished moments.
          </p>
        </div>
      </section>


      {error && (
        <div className="alert-banner alert-danger" style={{ marginBottom: '1.5rem' }}>
          <Icon name="heart" size={16} /> {error}
        </div>
      )}

      <div className="memories-gallery-grid">
        {loading && <p style={{ color: 'var(--color-text-muted)', padding: '2rem' }}>Loading memories...</p>}
        {!loading && memories.length === 0 && (
          <div className="empty-state-card">
            <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📸</div>
            <h3>No memories yet</h3>
            <p style={{ color: 'var(--color-text-muted)' }}>Check back later or ask your family to upload some memories for you.</p>
          </div>
        )}
          {memories.map((mem, i) => (
            <div key={mem._id || mem.memory_id || i} className="memory-card">
              {mem.photo_url && (
                <div className="memory-card-photo">
                  <img src={mem.photo_url} alt={mem.scene || 'Memory'} />
                </div>
              )}
              <div className="memory-card-body">
                <h3 className="memory-card-title">{mem.scene || mem.activity || 'Untitled Memory'}</h3>
                {mem.people && mem.people.length > 0 && (
                  <div className="memory-meta">
                    <Icon name="face" size={14} /> {mem.people.join(', ')}
                  </div>
                )}
                {mem.location && (
                  <div className="memory-meta">
                    <Icon name="walk" size={14} /> {mem.location}
                  </div>
                )}
                {mem.activity && (
                  <div className="memory-meta">
                    <Icon name="companion" size={14} /> {mem.activity}
                  </div>
                )}
                <div className="memory-card-actions">
                  <button className="btn btn-secondary btn-small" onClick={() => navigate(`/patient/quiz?memory=${mem._id || mem.memory_id}`)}>
                    <Icon name="puzzle" size={14} /> Practice Quiz
                  </button>
                </div>
              </div>
            </div>
          ))}
      </div>
    </div>
  );
}
