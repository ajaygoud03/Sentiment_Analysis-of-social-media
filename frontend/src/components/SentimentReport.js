import React from 'react';
import './SentimentReport.css';

const SentimentReport = ({ isLoading, error, result, postText }) => {
    if (isLoading) {
        return (
            <div className="card report-card">
                <h2>Analysis Report</h2>
                <div className="spinner"></div>
                <p>Analyzing...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="card report-card">
                <h2>Analysis Report</h2>
                <p className="error-text">{error}</p>
            </div>
        );
    }

    if (!result) {
        return (
            <div className="card report-card">
                <h2>Analysis Report</h2>
                <p>Submit a post URL to see the sentiment analysis report here.</p>
            </div>
        );
    }

    return (
        <div className="card report-card">
            <h2>Analysis Report</h2>
            <div className="post-text">
                <strong>Analyzed Text:</strong> "{postText}"
            </div>
            <div className={`sentiment-result ${result.sentiment?.toLowerCase()}`}>
                <span className="sentiment-label">Sentiment:</span>
                <span className="sentiment-value">{result.sentiment}</span>
            </div>
            <div className="confidence-score">
                <strong>Confidence:</strong> { (result.score * 100).toFixed(2) }%
            </div>
        </div>
    );
};

export default SentimentReport;