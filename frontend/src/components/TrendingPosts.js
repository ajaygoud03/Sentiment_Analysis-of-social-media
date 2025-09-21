// frontend/src/components/TrendingPosts.js
import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';

const TrendingPosts = () => {
    const [trends, setTrends] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState('');
    const [lastUpdated, setLastUpdated] = useState(null);

    const fetchTrends = useCallback(async () => {
        setIsLoading(true);
        setError('');

        try {
            const apiBase = process.env.REACT_APP_BACKEND_URL;
            if (!apiBase) throw new Error("REACT_APP_BACKEND_URL not set in .env");

            const response = await axios.get(`${apiBase}/api/trending`);
            if (!Array.isArray(response.data)) throw new Error("Unexpected backend response");

            setTrends(response.data);
            setLastUpdated(new Date());
        } catch (err) {
            console.error("Error fetching trends:", err);
            setError(err.response?.data?.error || err.message || 'Could not load trends.');
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchTrends();
        const intervalId = setInterval(fetchTrends, 300000); // every 5 min
        return () => clearInterval(intervalId);
    }, [fetchTrends]);

    return (
        <div className="card" style={{ padding: '20px', borderRadius: '10px', boxShadow: '0 2px 6px rgba(0,0,0,0.1)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
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
            ) : trends.length === 0 ? (
                <p>No trending posts found.</p>
            ) : (
                <ul style={{ padding: 0, margin: 0 }}>
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
                            <div><strong>Sentiment:</strong> {trend.sentiment}</div>
                            <div>{trend.text}</div>
                            <div style={{ fontSize: '0.8rem', color: '#505f79' }}>
                                Score: {trend.score?.toFixed(2) ?? 'N/A'}
                            </div>
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
};

export default TrendingPosts;
