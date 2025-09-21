// frontend/src/components/TrendingPosts.js
import React, { useState, useEffect } from 'react';
import axios from 'axios';

const TrendingPosts = () => {
    const [trends, setTrends] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState('');
    const [lastUpdated, setLastUpdated] = useState(null);

    const fetchTrends = async () => {
        setIsLoading(true);
        setError('');

        try {
            const apiBase = process.env.REACT_APP_BACKEND_URL || "http://127.0.0.1:8080";
            const response = await axios.get(`${apiBase}/api/trending`);
            setTrends(response.data);
            setLastUpdated(new Date());
        } catch (err) {
            console.error("Error fetching trends:", err);
            setError(err.response?.data?.error || 'Could not load trends.');
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchTrends(); // fetch only once on mount
    }, []);

    return (
        <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h2>Live Posts from X</h2>
                {lastUpdated && (
                    <span style={{ fontSize: '0.8rem', color: '#505f79' }}>
                        Updated at: {lastUpdated.toLocaleTimeString()}
                    </span>
                )}
            </div>
            {isLoading ? (
                <p>Loading posts...</p>
            ) : error ? (
                <p style={{ color: '#bf2600' }}>{error}</p>
            ) : (
                <ul>
                    {trends.map((trend, index) => (
                        <li
                            key={index}
                            style={{
                                marginBottom: '15px',
                                paddingBottom: '15px',
                                borderBottom: '1px solid #eee',
                                listStyle: 'none',
                            }}
                        >
                            {trend.text || trend} {/* support fallback data */}
                        </li>
                    ))}
                </ul>
            )}
            <button onClick={fetchTrends} style={{ marginTop: '10px' }}>
                Refresh Posts
            </button>
        </div>
    );
};

export default TrendingPosts;
