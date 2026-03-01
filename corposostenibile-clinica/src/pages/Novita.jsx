import { useState, useEffect } from 'react';
import newsService from '../services/newsService';
import logo from '../images/logo_foglia.png';
import './Novita.css';

function Novita() {
  const [newsList, setNewsList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState(null);

  useEffect(() => {
    fetchNews();
  }, []);

  const fetchNews = async () => {
    try {
      const data = await newsService.list({ per_page: 50 });
      if (data.success) {
        setNewsList(data.news);
      }
    } catch (err) {
      console.error('Errore caricamento novità:', err);
    } finally {
      setLoading(false);
    }
  };

  const toggleExpand = async (newsItem) => {
    if (expandedId === newsItem.id) {
      setExpandedId(null);
      return;
    }

    setExpandedId(newsItem.id);

    if (!newsItem.is_read) {
      try {
        await newsService.getDetail(newsItem.id);
        setNewsList((prev) =>
          prev.map((n) => (n.id === newsItem.id ? { ...n, is_read: true } : n))
        );
      } catch {
        // silent
      }
    }
  };

  const formatDate = (isoDate) => {
    if (!isoDate) return '';
    const d = new Date(isoDate);
    return d.toLocaleDateString('it-IT', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    });
  };

  return (
    <div className="novita-page">
      {/* Header */}
      <div className="novita-header-container">
        <div className="container">
          <div className="row justify-content-center">
            <div className="col-lg-8">
              <div className="novita-header-title">
                <img src={logo} alt="Corposostenibile" className="novita-header-logo" />
                <h1>Novità</h1>
                <p>Aggiornamenti, funzionalità e annunci dalla Suite Clinica</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="container pb-5">
        <div className="row justify-content-center">
          <div className="col-lg-8">
            {loading ? (
              <div className="novita-loading">
                <div className="novita-spinner" />
                <p>Caricamento novità...</p>
              </div>
            ) : newsList.length === 0 ? (
              <div className="novita-empty">
                <div className="novita-empty-icon">
                  <i className="mdi mdi-newspaper-variant-outline" />
                </div>
                <h3>Nessuna novità al momento</h3>
                <p>Quando ci saranno aggiornamenti sulla piattaforma, li troverai qui.</p>
              </div>
            ) : (
              <div className="novita-feed">
                {newsList.map((item) => (
                  <div
                    key={item.id}
                    className={`novita-card${item.is_pinned ? ' is-pinned' : ''}`}
                  >
                    <div className="novita-card-header" onClick={() => toggleExpand(item)}>
                      <div className="novita-card-icon">
                        <i className={`mdi ${item.is_pinned ? 'mdi-pin' : 'mdi-bullhorn-outline'}`} />
                      </div>
                      <div className="novita-card-body">
                        <div className="novita-card-title-row">
                          <h3 className="novita-card-title">{item.title}</h3>
                          {!item.is_read && <span className="novita-badge-new">Nuovo</span>}
                          {item.is_pinned && <span className="novita-badge-pinned">In evidenza</span>}
                        </div>
                        {item.summary && <p className="novita-card-summary">{item.summary}</p>}
                      </div>
                      <i className={`mdi mdi-chevron-right novita-card-chevron${expandedId === item.id ? ' expanded' : ''}`} />
                    </div>

                    <div className="novita-card-meta">
                      <i className="mdi mdi-calendar-outline" />
                      <span>{formatDate(item.published_at)}</span>
                      {item.author && (
                        <>
                          <span>·</span>
                          <i className="mdi mdi-account-outline" />
                          <span>{item.author}</span>
                        </>
                      )}
                    </div>

                    {expandedId === item.id && (
                      <div
                        className="novita-card-content"
                        dangerouslySetInnerHTML={{ __html: item.content }}
                      />
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default Novita;
